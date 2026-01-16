"""
Tests for search API endpoint.

Tests the GET /api/v1/search/ endpoint.
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
        username='admin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.fixture
def item_manager(db):
    """Create an item manager user."""
    return User.objects.create_user(
        username='manager',
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
def items(db, location, category, super_admin, item_manager):
    """Create test items for search."""
    items = []
    
    # Item 1: Laptop with specific SKU
    items.append(Item.objects.create(
        name='Dell Laptop XPS 15',
        sku='LAPTOP-001',
        barcode='BC001',
        location=location,
        category=category,
        owner=super_admin,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        is_active=True,
    ))
    
    # Item 2: Another laptop
    items.append(Item.objects.create(
        name='HP Laptop ProBook',
        sku='LAPTOP-002',
        barcode='BC002',
        location=location,
        category=category,
        owner=super_admin,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        is_active=True,
    ))
    
    # Item 3: Mouse (consumable)
    items.append(Item.objects.create(
        name='Wireless Mouse',
        sku='MOUSE-001',
        barcode='BC003',
        location=location,
        category=category,
        owner=item_manager,
        type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK,
        quantity=10,
        is_active=True,
    ))
    
    # Item 4: Inactive item
    items.append(Item.objects.create(
        name='Old Keyboard',
        sku='KEYBOARD-001',
        barcode='BC004',
        location=location,
        category=category,
        owner=super_admin,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        is_active=False,
    ))
    
    return items


@pytest.mark.django_db
class TestSearchEndpoint:
    """Tests for GET /api/v1/search/"""
    
    def test_search_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot search."""
        url = reverse('inventory:search')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_search_no_keyword(self, api_client, super_admin, items):
        """Test search without keyword returns all active items."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Should return 3 active items (excluding inactive)
        assert response.data['count'] == 3
    
    def test_search_with_keyword(self, api_client, super_admin, items):
        """Test search with keyword."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'laptop'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return 2 laptop items
        assert response.data['count'] == 2
        
        # Check that results contain laptop items
        skus = [item['sku'] for item in response.data['results']]
        assert 'LAPTOP-001' in skus
        assert 'LAPTOP-002' in skus
    
    def test_search_exact_sku_match(self, api_client, super_admin, items):
        """Test that exact SKU match has highest priority."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'LAPTOP-001'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
        # Exact match should be first
        assert response.data['results'][0]['sku'] == 'LAPTOP-001'
    
    def test_search_sku_prefix_match(self, api_client, super_admin, items):
        """Test SKU prefix matching."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'LAPTOP'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return both laptop items
        assert response.data['count'] == 2
    
    def test_search_inactive_excluded_by_default(self, api_client, super_admin, items):
        """Test that inactive items are excluded by default."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'keyboard'})
        
        assert response.status_code == status.HTTP_200_OK
        # Inactive keyboard should not be returned
        assert response.data['count'] == 0
    
    def test_search_include_inactive_super_admin(self, api_client, super_admin, items):
        """Test that Super_Admin can include inactive items."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'keyboard', 'include_inactive': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return the inactive keyboard
        assert response.data['count'] == 1
        assert response.data['results'][0]['sku'] == 'KEYBOARD-001'
    
    def test_search_include_inactive_non_admin_ignored(self, api_client, item_manager, items):
        """Test that non-admin users cannot include inactive items."""
        api_client.force_authenticate(user=item_manager)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'keyboard', 'include_inactive': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should not return inactive items even with include_inactive=true
        assert response.data['count'] == 0
    
    def test_search_data_isolation_item_manager(self, api_client, item_manager, items):
        """Test that Item_Manager only sees owned items."""
        api_client.force_authenticate(user=item_manager)
        url = reverse('inventory:search')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Item_Manager should only see their own items (mouse)
        assert response.data['count'] == 1
        assert response.data['results'][0]['sku'] == 'MOUSE-001'
    
    def test_search_filter_by_type(self, api_client, super_admin, items):
        """Test filtering by item type."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'type': 'consumable'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return only consumable items
        assert response.data['count'] == 1
        assert response.data['results'][0]['type'] == 'consumable'
    
    def test_search_filter_by_status(self, api_client, super_admin, items):
        """Test filtering by item status."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'status': 'in_stock'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return only in_stock items
        assert response.data['count'] == 1
        assert response.data['results'][0]['status'] == 'in_stock'
    
    def test_search_filter_by_category(self, api_client, super_admin, items, category):
        """Test filtering by category."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'category': category.id})
        
        assert response.status_code == status.HTTP_200_OK
        # All active items are in the same category
        assert response.data['count'] == 3
    
    def test_search_filter_by_location(self, api_client, super_admin, items, location):
        """Test filtering by location."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'location': location.id})
        
        assert response.status_code == status.HTTP_200_OK
        # All active items are in the same location
        assert response.data['count'] == 3
    
    def test_search_combined_keyword_and_filter(self, api_client, super_admin, items):
        """Test combining keyword search with filters."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': 'laptop', 'type': 'reusable'})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return laptop items that are reusable
        assert response.data['count'] == 2
    
    def test_search_empty_keyword_stripped(self, api_client, super_admin, items):
        """Test that empty/whitespace keyword is treated as no keyword."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'keyword': '   '})
        
        assert response.status_code == status.HTTP_200_OK
        # Should return all active items (no keyword filter)
        assert response.data['count'] == 3
    
    def test_search_pagination(self, api_client, super_admin, items):
        """Test search pagination."""
        api_client.force_authenticate(user=super_admin)
        url = reverse('inventory:search')
        response = api_client.get(url, {'page_size': 2})
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert len(response.data['results']) <= 2
    
    def test_search_read_only_user_can_search(self, api_client, read_only_user, items):
        """Test that read-only users can search."""
        api_client.force_authenticate(user=read_only_user)
        url = reverse('inventory:search')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Read-only users can see all active items
        assert response.data['count'] == 3
