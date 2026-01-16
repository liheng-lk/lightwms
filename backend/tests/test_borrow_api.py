"""
Tests for borrow/return API endpoints.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User, UserRole
from apps.inventory.models import Warehouse, Location, Category, Item, ItemType, ItemStatus
from apps.operations.models import BorrowRecord, BorrowStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        username='admin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def item_manager():
    return User.objects.create_user(
        username='manager',
        password='testpass123',
        role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def read_only_user():
    return User.objects.create_user(
        username='readonly',
        password='testpass123',
        role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def borrower_user():
    return User.objects.create_user(
        username='borrower',
        password='testpass123',
        role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def warehouse():
    return Warehouse.objects.create(
        code='WH-001',
        name='Test Warehouse'
    )


@pytest.fixture
def location(warehouse):
    return Location.objects.create(
        warehouse=warehouse,
        code='LOC-001',
        name='Test Location'
    )


@pytest.fixture
def reusable_item(location, item_manager):
    return Item.objects.create(
        name='Test Reusable Item',
        sku='SKU-REUSABLE-001',
        location=location,
        owner=item_manager,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE
    )


@pytest.fixture
def consumable_item(location, item_manager):
    return Item.objects.create(
        name='Test Consumable Item',
        sku='SKU-CONSUMABLE-001',
        location=location,
        owner=item_manager,
        type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK,
        quantity=100
    )


@pytest.mark.django_db
class TestBorrowEndpoint:
    """Tests for POST /api/v1/items/{id}/borrow/"""
    
    def test_borrow_item_success(self, api_client, item_manager, reusable_item, borrower_user):
        """Test successful borrow operation."""
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
                'notes': 'Test borrow'
            },
            format='json'
        )
        
        assert response.status_code == 201
        assert response.data['item'] == reusable_item.id
        assert response.data['borrower'] == borrower_user.id
        assert response.data['status'] == 'active'
        assert response.data['computed_status'] == 'active'
        
        # Verify item status changed
        reusable_item.refresh_from_db()
        assert reusable_item.status == ItemStatus.BORROWED
    
    def test_borrow_item_super_admin(self, api_client, super_admin, reusable_item, borrower_user):
        """Test super admin can borrow any item."""
        api_client.force_authenticate(user=super_admin)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 201
    
    def test_borrow_item_already_borrowed(self, api_client, item_manager, reusable_item, borrower_user):
        """Test cannot borrow already borrowed item."""
        api_client.force_authenticate(user=item_manager)
        
        # First borrow
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Second borrow should fail
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 409
        assert response.data['code'] == 'ITEM_ALREADY_BORROWED'
    
    def test_borrow_consumable_item_fails(self, api_client, item_manager, consumable_item, borrower_user):
        """Test cannot borrow consumable item."""
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{consumable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 409
        assert response.data['code'] == 'INVALID_ITEM_TYPE'
    
    def test_borrow_inactive_item_fails(self, api_client, item_manager, reusable_item, borrower_user):
        """Test cannot borrow inactive item."""
        reusable_item.is_active = False
        reusable_item.save()
        
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 409
        assert response.data['code'] == 'RESOURCE_INACTIVE'
    
    def test_borrow_item_read_only_user_forbidden(self, api_client, read_only_user, reusable_item, borrower_user):
        """Test read-only user cannot borrow items."""
        api_client.force_authenticate(user=read_only_user)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 403
    
    def test_borrow_item_non_owner_forbidden(self, api_client, reusable_item, borrower_user):
        """Test item manager cannot borrow items they don't own."""
        other_manager = User.objects.create_user(
            username='other_manager',
            password='testpass123',
            role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 404  # Data isolation returns 404
    
    def test_borrow_item_invalid_borrower(self, api_client, item_manager, reusable_item):
        """Test cannot borrow with invalid borrower ID."""
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': 99999,  # Non-existent user
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 409
        assert response.data['code'] == 'INVALID_BORROWER'
    
    def test_borrow_item_past_return_date(self, api_client, item_manager, reusable_item, borrower_user):
        """Test cannot borrow with past return date."""
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() - timedelta(days=1)).isoformat(),
            },
            format='json'
        )
        
        assert response.status_code == 400


@pytest.mark.django_db
class TestReturnEndpoint:
    """Tests for POST /api/v1/items/{id}/return/"""
    
    def test_return_item_by_owner(self, api_client, item_manager, reusable_item, borrower_user):
        """Test owner can return borrowed item."""
        # First borrow the item
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Return the item
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {
                'return_notes': 'Returned in good condition',
                'condition': 'Good'
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert response.data['status'] == 'returned'
        assert response.data['computed_status'] == 'returned'
        assert response.data['condition'] == 'Good'
        
        # Verify item status changed
        reusable_item.refresh_from_db()
        assert reusable_item.status == ItemStatus.AVAILABLE
    
    def test_return_item_by_borrower(self, api_client, item_manager, reusable_item, borrower_user):
        """Test borrower can return item but cannot set condition."""
        # First borrow the item
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Borrower returns the item
        api_client.force_authenticate(user=borrower_user)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {
                'return_notes': 'Returning item',
                'condition': 'Damaged'  # This should be ignored
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert response.data['status'] == 'returned'
        assert response.data['condition'] == ''  # Condition not set by borrower
    
    def test_return_item_by_super_admin(self, api_client, super_admin, item_manager, reusable_item, borrower_user):
        """Test super admin can return any item."""
        # First borrow the item
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Super admin returns the item
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {
                'return_notes': 'Admin return',
                'condition': 'Good'
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert response.data['condition'] == 'Good'
    
    def test_return_item_not_borrowed(self, api_client, item_manager, reusable_item):
        """Test cannot return item that is not borrowed."""
        api_client.force_authenticate(user=item_manager)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {
                'return_notes': 'Test return'
            },
            format='json'
        )
        
        assert response.status_code == 409
        assert response.data['code'] == 'NO_ACTIVE_BORROW'
    
    def test_return_item_unauthorized_user(self, api_client, item_manager, reusable_item, borrower_user):
        """Test unauthorized user cannot return item."""
        # First borrow the item
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Another user tries to return
        other_user = User.objects.create_user(
            username='other_user',
            password='testpass123',
            role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_user)
        
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {
                'return_notes': 'Test return'
            },
            format='json'
        )
        
        assert response.status_code == 404  # Data isolation returns 404


@pytest.mark.django_db
class TestBorrowRecordListEndpoint:
    """Tests for GET /api/v1/borrow-records/"""
    
    def test_list_borrow_records(self, api_client, item_manager, reusable_item, borrower_user):
        """Test listing borrow records."""
        # Create a borrow record
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        response = api_client.get('/api/v1/borrow-records/')
        
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['item'] == reusable_item.id
    
    def test_list_borrow_records_data_isolation(self, api_client, item_manager, reusable_item, borrower_user):
        """Test item manager only sees their own items' records."""
        # Create a borrow record
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        # Another manager should not see this record
        other_manager = User.objects.create_user(
            username='other_manager',
            password='testpass123',
            role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_manager)
        
        response = api_client.get('/api/v1/borrow-records/')
        
        assert response.status_code == 200
        assert response.data['count'] == 0
    
    def test_list_borrow_records_filter_by_status(self, api_client, item_manager, reusable_item, borrower_user):
        """Test filtering borrow records by status."""
        api_client.force_authenticate(user=item_manager)
        
        # Create and return a borrow
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Returned'},
            format='json'
        )
        
        # Filter by returned status
        response = api_client.get('/api/v1/borrow-records/?status=returned')
        
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['status'] == 'returned'


@pytest.mark.django_db
class TestRecentBorrowersEndpoint:
    """Tests for GET /api/v1/recent-borrowers/"""
    
    def test_get_recent_borrowers(self, api_client, item_manager, reusable_item, borrower_user):
        """Test getting recent borrowers."""
        api_client.force_authenticate(user=item_manager)
        
        # Create a borrow record
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': borrower_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json'
        )
        
        response = api_client.get('/api/v1/recent-borrowers/')
        
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['id'] == borrower_user.id
        assert response.data[0]['username'] == borrower_user.username
    
    def test_recent_borrowers_read_only_user_forbidden(self, api_client, read_only_user):
        """Test read-only user cannot access recent borrowers."""
        api_client.force_authenticate(user=read_only_user)
        
        response = api_client.get('/api/v1/recent-borrowers/')
        
        assert response.status_code == 403


@pytest.mark.django_db
class TestBorrowRecordComputedStatus:
    """Tests for BorrowRecord computed_status property."""
    
    def test_computed_status_active(self, item_manager, reusable_item, borrower_user):
        """Test computed status is 'active' for active borrow."""
        record = BorrowRecord.objects.create(
            item=reusable_item,
            borrower=borrower_user,
            operator=item_manager,
            expected_return_date=date.today() + timedelta(days=7),
            status=BorrowStatus.ACTIVE
        )
        
        assert record.computed_status == 'active'
    
    def test_computed_status_overdue(self, item_manager, reusable_item, borrower_user):
        """Test computed status is 'overdue' for overdue borrow."""
        record = BorrowRecord.objects.create(
            item=reusable_item,
            borrower=borrower_user,
            operator=item_manager,
            expected_return_date=date.today() - timedelta(days=1),  # Past date
            status=BorrowStatus.ACTIVE
        )
        
        assert record.computed_status == 'overdue'
    
    def test_computed_status_returned(self, item_manager, reusable_item, borrower_user):
        """Test computed status is 'returned' for returned borrow."""
        record = BorrowRecord.objects.create(
            item=reusable_item,
            borrower=borrower_user,
            operator=item_manager,
            expected_return_date=date.today() + timedelta(days=7),
            actual_return_datetime=timezone.now(),
            status=BorrowStatus.RETURNED
        )
        
        assert record.computed_status == 'returned'
