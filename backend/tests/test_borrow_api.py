"""Tests for borrow/return API endpoints."""
from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        username='admin', password='testpass123', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def item_manager():
    return User.objects.create_user(
        username='manager', password='testpass123', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def read_only_user():
    return User.objects.create_user(
        username='readonly', password='testpass123', role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def borrower_user():
    return User.objects.create_user(
        username='borrower', password='testpass123', role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def warehouse():
    return Warehouse.objects.create(code='WH-001', name='Test Warehouse')


@pytest.fixture
def location(warehouse):
    return Location.objects.create(
        warehouse=warehouse, code='LOC-001', name='Test Location'
    )


@pytest.fixture
def reusable_item(location, item_manager):
    return Item.objects.create(
        name='Test Reusable Item', sku='SKU-REUSABLE-001',
        location=location, owner=item_manager, type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
    )


@pytest.fixture
def consumable_item(location, item_manager):
    return Item.objects.create(
        name='Test Consumable Item', sku='SKU-CONSUMABLE-001',
        location=location, owner=item_manager, type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK, quantity=100,
    )


def borrow_payload(borrower, days=7):
    return {
        'borrower': borrower.id,
        'expected_return_date': (date.today() + timedelta(days=days)).isoformat(),
    }


@pytest.mark.django_db
class TestBorrowEndpoint:
    def test_borrow_item_success(self, api_client, item_manager, reusable_item, borrower_user):
        api_client.force_authenticate(user=item_manager)
        payload = borrow_payload(borrower_user)
        payload['notes'] = 'Test borrow'
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/', payload, format='json'
        )
        assert response.status_code == 201
        assert response.data['item'] == reusable_item.id
        assert response.data['borrower'] == borrower_user.id
        assert response.data['status'] == 'active'
        assert response.data['computed_status'] == 'active'
        reusable_item.refresh_from_db()
        assert reusable_item.status == ItemStatus.BORROWED

    def test_borrow_item_super_admin(self, api_client, super_admin, reusable_item, borrower_user):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        assert response.status_code == 201

    def test_borrow_item_already_borrowed(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        url = f'/api/v1/items/{reusable_item.id}/borrow/'
        api_client.post(url, borrow_payload(borrower_user), format='json')
        response = api_client.post(url, borrow_payload(borrower_user), format='json')
        assert response.status_code == 409
        assert response.data['code'] == 'ITEM_ALREADY_BORROWED'

    def test_borrow_consumable_item_fails(
        self, api_client, item_manager, consumable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(
            f'/api/v1/items/{consumable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        assert response.status_code == 409
        assert response.data['code'] == 'INVALID_ITEM_TYPE'

    def test_borrow_inactive_item_fails(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        reusable_item.is_active = False
        reusable_item.save(update_fields=['is_active'])
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        assert response.status_code == 409
        assert response.data['code'] == 'RESOURCE_INACTIVE'

    def test_borrow_item_read_only_user_forbidden(
        self, api_client, read_only_user, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        assert response.status_code == 403

    def test_any_item_manager_can_borrow_inventory_item(
        self, api_client, reusable_item, borrower_user
    ):
        other_manager = User.objects.create_user(
            username='other_manager', password='testpass123', role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        assert response.status_code == 201

    def test_borrow_item_invalid_borrower(self, api_client, item_manager, reusable_item):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            {
                'borrower': 99999,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json',
        )
        assert response.status_code == 409
        assert response.data['code'] == 'INVALID_BORROWER'

    def test_borrow_item_past_return_date(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user, days=-1), format='json'
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestReturnEndpoint:
    def _borrow(self, api_client, item_manager, reusable_item, borrower_user):
        api_client.force_authenticate(user=item_manager)
        return api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )

    def test_return_item_by_manager(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        self._borrow(api_client, item_manager, reusable_item, borrower_user)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Returned in good condition', 'condition': 'Good'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['status'] == 'returned'
        assert response.data['computed_status'] == 'returned'
        assert response.data['condition'] == 'Good'
        reusable_item.refresh_from_db()
        assert reusable_item.status == ItemStatus.AVAILABLE

    def test_return_item_by_borrower(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        self._borrow(api_client, item_manager, reusable_item, borrower_user)
        api_client.force_authenticate(user=borrower_user)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Returning item', 'condition': 'Damaged'}, format='json'
        )
        assert response.status_code == 200
        assert response.data['status'] == 'returned'
        assert response.data['condition'] == ''

    def test_return_item_by_super_admin(
        self, api_client, super_admin, item_manager, reusable_item, borrower_user
    ):
        self._borrow(api_client, item_manager, reusable_item, borrower_user)
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Admin return', 'condition': 'Good'}, format='json'
        )
        assert response.status_code == 200
        assert response.data['condition'] == 'Good'

    def test_return_item_not_borrowed(self, api_client, item_manager, reusable_item):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Test return'}, format='json'
        )
        assert response.status_code == 409
        assert response.data['code'] == 'NO_ACTIVE_BORROW'

    def test_other_item_manager_can_process_return(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        self._borrow(api_client, item_manager, reusable_item, borrower_user)
        other_manager = User.objects.create_user(
            username='return_manager', password='testpass123', role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_manager)
        response = api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Cross-manager return'}, format='json'
        )
        assert response.status_code == 200
        assert response.data['status'] == BorrowStatus.RETURNED


@pytest.mark.django_db
class TestBorrowRecordListEndpoint:
    def test_list_borrow_records(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        response = api_client.get('/api/v1/borrow-records/')
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['item'] == reusable_item.id

    def test_item_manager_sees_inventory_wide_borrow_records(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        other_manager = User.objects.create_user(
            username='record_manager', password='testpass123', role=UserRole.ITEM_MANAGER
        )
        api_client.force_authenticate(user=other_manager)
        response = api_client.get('/api/v1/borrow-records/')
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['item'] == reusable_item.id

    def test_list_borrow_records_filter_by_status(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/return/',
            {'return_notes': 'Returned'}, format='json'
        )
        response = api_client.get('/api/v1/borrow-records/?status=returned')
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['status'] == 'returned'


@pytest.mark.django_db
class TestRecentBorrowersEndpoint:
    def test_get_recent_borrowers(
        self, api_client, item_manager, reusable_item, borrower_user
    ):
        api_client.force_authenticate(user=item_manager)
        api_client.post(
            f'/api/v1/items/{reusable_item.id}/borrow/',
            borrow_payload(borrower_user), format='json'
        )
        response = api_client.get('/api/v1/recent-borrowers/')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['id'] == borrower_user.id
        assert response.data[0]['username'] == borrower_user.username

    def test_recent_borrowers_read_only_user_forbidden(self, api_client, read_only_user):
        api_client.force_authenticate(user=read_only_user)
        assert api_client.get('/api/v1/recent-borrowers/').status_code == 403


@pytest.mark.django_db
class TestBorrowRecordComputedStatus:
    def test_computed_status_active(self, item_manager, reusable_item, borrower_user):
        record = BorrowRecord.objects.create(
            item=reusable_item, borrower=borrower_user, operator=item_manager,
            expected_return_date=date.today() + timedelta(days=7), status=BorrowStatus.ACTIVE,
        )
        assert record.computed_status == 'active'

    def test_computed_status_overdue(self, item_manager, reusable_item, borrower_user):
        record = BorrowRecord.objects.create(
            item=reusable_item, borrower=borrower_user, operator=item_manager,
            expected_return_date=date.today() - timedelta(days=1), status=BorrowStatus.ACTIVE,
        )
        assert record.computed_status == 'overdue'

    def test_computed_status_returned(self, item_manager, reusable_item, borrower_user):
        record = BorrowRecord.objects.create(
            item=reusable_item, borrower=borrower_user, operator=item_manager,
            expected_return_date=date.today() + timedelta(days=7),
            actual_return_datetime=timezone.now(), status=BorrowStatus.RETURNED,
        )
        assert record.computed_status == 'returned'
