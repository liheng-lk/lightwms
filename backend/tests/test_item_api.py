"""
Tests for Item API endpoints.

Tests cover:
- GET/POST /api/v1/items/
- GET/PATCH /api/v1/items/{id}/
- POST /api/v1/items/{id}/deactivate/
- POST /api/v1/items/{id}/generate-barcode/

Requirements: 6.1-6.7, 6.12-6.15
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole
from apps.inventory.models import Warehouse, Location, Category, Item, ItemType, ItemStatus


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def super_admin(db):
    """Create a super admin user."""
    return User.objects.create_user(
        username='superadmin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.fixture
def item_manager(db):
    """Create an item manager user."""
    return User.objects.create_user(
        username='itemmanager',
        password='testpass123',
        role=UserRole.ITEM_MANAGER,
        is_active=True,
    )


@pytest.fixture
def read_only_user(db):
    """Create a read-only user."""
    return User.objects.create_user(
        username='readonly',
        password='testpass123',
        role=UserRole.READ_ONLY_USER,
        is_active=True,
    )


@pytest.fixture
def warehouse(db):
    """Create a test warehouse."""
    return Warehouse.objects.create(
        code='WH-001',
        name='Test Warehouse',
        is_active=True,
    )


@pytest.fixture
def location(db, warehouse):
    """Create a test location."""
    return Location.objects.create(
        warehouse=warehouse,
        code='LOC-001',
        name='Test Location',
        is_active=True,
    )


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(
        name='Test Category',
        is_active=True,
    )


@pytest.fixture
def reusable_item(db, location, category, item_manager):
    """Create a test reusable item."""
    return Item.objects.create(
        name='Test Reusable Item',
        sku='SKU-001',
        location=location,
        category=category,
        owner=item_manager,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        is_active=True,
    )


@pytest.fixture
def consumable_item(db, location, category, item_manager):
    """Create a test consumable item."""
    return Item.objects.create(
        name='Test Consumable Item',
        sku='SKU-002',
        location=location,
        category=category,
        owner=item_manager,
        type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK,
        quantity=100,
        is_active=True,
    )


class TestItemListEndpoint:
    """Tests for GET /api/v1/items/"""
    
    def test_list_items_authenticated(self, api_client, super_admin, reusable_item):
        """Test listing items as authenticated user."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1
    
    def test_list_items_unauthenticated(self, api_client, reusable_item):
        """Test listing items without authentication."""
        response = api_client.get('/api/v1/items/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_items_data_isolation_item_manager(self, api_client, item_manager, super_admin, location, category):
        """Test that item manager only sees their own items."""
        # Create item owned by item_manager
        Item.objects.create(
            name='Manager Item',
            sku='SKU-MGR-001',
            location=location,
            category=category,
            owner=item_manager,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        # Create item owned by super_admin
        Item.objects.create(
            name='Admin Item',
            sku='SKU-ADM-001',
            location=location,
            category=category,
            owner=super_admin,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        api_client.force_authenticate(user=item_manager)
        response = api_client.get('/api/v1/items/')
        
        assert response.status_code == status.HTTP_200_OK
        # Item manager should only see their own items
        for item in response.data['results']:
            assert item['owner'] == item_manager.id
    
    def test_list_items_filter_by_type(self, api_client, super_admin, reusable_item, consumable_item):
        """Test filtering items by type."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/', {'type': 'reusable'})
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['type'] == 'reusable'
    
    def test_list_items_filter_by_status(self, api_client, super_admin, reusable_item):
        """Test filtering items by status."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/', {'status': 'available'})
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['status'] == 'available'


class TestItemCreateEndpoint:
    """Tests for POST /api/v1/items/"""
    
    def test_create_reusable_item(self, api_client, super_admin, location, category):
        """Test creating a reusable item."""
        api_client.force_authenticate(user=super_admin)
        data = {
            'name': 'New Reusable Item',
            'sku': 'SKU-NEW-001',
            'location': location.id,
            'category': category.id,
            'type': 'reusable',
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Reusable Item'
        assert response.data['sku'] == 'SKU-NEW-001'
        assert response.data['type'] == 'reusable'
        assert response.data['status'] == 'available'  # Requirement 6.5
    
    def test_create_consumable_item(self, api_client, super_admin, location, category):
        """Test creating a consumable item with quantity."""
        api_client.force_authenticate(user=super_admin)
        data = {
            'name': 'New Consumable Item',
            'sku': 'SKU-NEW-002',
            'location': location.id,
            'category': category.id,
            'type': 'consumable',
            'quantity': 50,
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['type'] == 'consumable'
        assert response.data['status'] == 'in_stock'  # Requirement 6.6
        assert response.data['quantity'] == 50
    
    def test_create_consumable_item_zero_quantity(self, api_client, super_admin, location, category):
        """Test creating a consumable item with zero quantity."""
        api_client.force_authenticate(user=super_admin)
        data = {
            'name': 'Empty Consumable Item',
            'sku': 'SKU-NEW-003',
            'location': location.id,
            'category': category.id,
            'type': 'consumable',
            'quantity': 0,
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'out_of_stock'  # Requirement 6.6
    
    def test_create_item_default_owner(self, api_client, item_manager, location, category):
        """Test that owner defaults to creating user."""
        api_client.force_authenticate(user=item_manager)
        data = {
            'name': 'Item Without Owner',
            'sku': 'SKU-NEW-004',
            'location': location.id,
            'type': 'reusable',
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['owner'] == item_manager.id  # Requirement 6.2
    
    def test_create_item_duplicate_sku(self, api_client, super_admin, location, reusable_item):
        """Test that duplicate SKU returns 409."""
        api_client.force_authenticate(user=super_admin)
        data = {
            'name': 'Duplicate SKU Item',
            'sku': reusable_item.sku,  # Duplicate SKU
            'location': location.id,
            'type': 'reusable',
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_409_CONFLICT  # Requirement 6.3
        # Note: In PostgreSQL, this returns DUPLICATE_SKU; in SQLite, INTEGRITY_ERROR
        # Both are valid 409 responses for duplicate SKU constraint violation
        assert response.data['code'] in ('DUPLICATE_SKU', 'INTEGRITY_ERROR')
    
    def test_create_item_read_only_user_forbidden(self, api_client, read_only_user, location):
        """Test that read-only user cannot create items."""
        api_client.force_authenticate(user=read_only_user)
        data = {
            'name': 'Forbidden Item',
            'sku': 'SKU-FORBIDDEN',
            'location': location.id,
            'type': 'reusable',
        }
        response = api_client.post('/api/v1/items/', data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestItemDetailEndpoint:
    """Tests for GET /api/v1/items/{id}/"""
    
    def test_get_item_detail(self, api_client, super_admin, reusable_item):
        """Test getting item detail."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f'/api/v1/items/{reusable_item.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == reusable_item.id
        assert response.data['name'] == reusable_item.name
    
    def test_get_item_not_found(self, api_client, super_admin):
        """Test getting non-existent item."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/99999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_item_data_isolation(self, api_client, item_manager, super_admin, location, category):
        """Test that item manager cannot see other's items."""
        # Create item owned by super_admin
        other_item = Item.objects.create(
            name='Other Item',
            sku='SKU-OTHER-001',
            location=location,
            category=category,
            owner=super_admin,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        api_client.force_authenticate(user=item_manager)
        response = api_client.get(f'/api/v1/items/{other_item.id}/')
        
        # Should return 404 (not 403) for security
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestItemUpdateEndpoint:
    """Tests for PATCH /api/v1/items/{id}/"""
    
    def test_update_item(self, api_client, super_admin, reusable_item):
        """Test updating an item."""
        api_client.force_authenticate(user=super_admin)
        data = {'name': 'Updated Item Name'}
        response = api_client.patch(f'/api/v1/items/{reusable_item.id}/', data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Item Name'
    
    def test_update_item_owner_can_update(self, api_client, item_manager, reusable_item):
        """Test that owner can update their item."""
        api_client.force_authenticate(user=item_manager)
        data = {'name': 'Owner Updated Name'}
        response = api_client.patch(f'/api/v1/items/{reusable_item.id}/', data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Owner Updated Name'
    
    def test_update_item_non_owner_forbidden(self, api_client, super_admin, location, category):
        """Test that non-owner item manager cannot update."""
        # Create another item manager
        other_manager = User.objects.create_user(
            username='othermanager',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        # Create item owned by other_manager
        other_item = Item.objects.create(
            name='Other Manager Item',
            sku='SKU-OTHER-MGR',
            location=location,
            category=category,
            owner=other_manager,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        # Create a new item manager who doesn't own the item
        non_owner = User.objects.create_user(
            username='nonowner',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        api_client.force_authenticate(user=non_owner)
        data = {'name': 'Forbidden Update'}
        response = api_client.patch(f'/api/v1/items/{other_item.id}/', data)
        
        # Should return 404 (not 403) for security
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_item_read_only_user_forbidden(self, api_client, read_only_user, reusable_item):
        """Test that read-only user cannot update items."""
        api_client.force_authenticate(user=read_only_user)
        data = {'name': 'Forbidden Update'}
        response = api_client.patch(f'/api/v1/items/{reusable_item.id}/', data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestItemDeactivateEndpoint:
    """Tests for POST /api/v1/items/{id}/deactivate/"""
    
    def test_deactivate_item(self, api_client, super_admin, reusable_item):
        """Test deactivating an item."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_active'] is False  # Requirement 6.12
    
    def test_deactivate_item_owner_can_deactivate(self, api_client, item_manager, reusable_item):
        """Test that owner can deactivate their item."""
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_active'] is False  # Requirement 4.12
    
    def test_deactivate_item_non_owner_forbidden(self, api_client, super_admin, location, category):
        """Test that non-owner item manager cannot deactivate."""
        # Create another item manager
        other_manager = User.objects.create_user(
            username='othermanager2',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        # Create item owned by other_manager
        other_item = Item.objects.create(
            name='Other Manager Item 2',
            sku='SKU-OTHER-MGR-2',
            location=location,
            category=category,
            owner=other_manager,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        # Create a new item manager who doesn't own the item
        non_owner = User.objects.create_user(
            username='nonowner2',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        api_client.force_authenticate(user=non_owner)
        response = api_client.post(f'/api/v1/items/{other_item.id}/deactivate/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_deactivate_item_read_only_user_forbidden(self, api_client, read_only_user, reusable_item):
        """Test that read-only user cannot deactivate items."""
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestItemGenerateBarcodeEndpoint:
    """Tests for POST /api/v1/items/{id}/generate-barcode/"""
    
    def test_generate_barcode(self, api_client, super_admin, reusable_item):
        """Test generating barcode for an item."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'barcode' in response.data
        assert 'label_png_base64' in response.data
        assert response.data['barcode'].startswith('BC')  # Requirement 6.7
    
    def test_generate_barcode_owner_can_generate(self, api_client, item_manager, reusable_item):
        """Test that owner can generate barcode for their item."""
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'barcode' in response.data
    
    def test_generate_barcode_non_owner_forbidden(self, api_client, super_admin, location, category):
        """Test that non-owner item manager cannot generate barcode."""
        # Create another item manager
        other_manager = User.objects.create_user(
            username='othermanager3',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        # Create item owned by other_manager
        other_item = Item.objects.create(
            name='Other Manager Item 3',
            sku='SKU-OTHER-MGR-3',
            location=location,
            category=category,
            owner=other_manager,
            type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE,
        )
        
        # Create a new item manager who doesn't own the item
        non_owner = User.objects.create_user(
            username='nonowner3',
            password='testpass123',
            role=UserRole.ITEM_MANAGER,
            is_active=True,
        )
        
        api_client.force_authenticate(user=non_owner)
        response = api_client.post(f'/api/v1/items/{other_item.id}/generate-barcode/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_generate_barcode_read_only_user_forbidden(self, api_client, read_only_user, reusable_item):
        """Test that read-only user cannot generate barcodes."""
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
