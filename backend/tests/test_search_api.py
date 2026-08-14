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

    items.append(Item.objects.create(
        name='Dell Laptop XPS 15', sku='LAPTOP-001', barcode='BC001',
        location=location, category=category, owner=super_admin,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE, is_active=True,
    ))
    items.append(Item.objects.create(
        name='HP Laptop ProBook', sku='LAPTOP-002', barcode='BC002',
        location=location, category=category, owner=super_admin,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE, is_active=True,
    ))
    items.append(Item.objects.create(
        name='Wireless Mouse', sku='MOUSE-001', barcode='BC003',
        location=location, category=category, owner=item_manager,
        type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
        quantity=10, is_active=True,
    ))
    items.append(Item.objects.create(
        name='Old Keyboard', sku='KEYBOARD-001', barcode='BC004',
        location=location, category=category, owner=super_admin,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE, is_active=False,
    ))
    return items


@pytest.mark.django_db
class TestSearchEndpoint:
    """Tests for GET /api/v1/search/."""

    def test_search_unauthenticated(self, api_client):
        url = reverse('inventory:search')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_no_keyword(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_search_with_keyword(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'keyword': 'laptop'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        skus = [item['sku'] for item in response.data['results']]
        assert 'LAPTOP-001' in skus
        assert 'LAPTOP-002' in skus

    def test_search_exact_sku_match(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'keyword': 'LAPTOP-001'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
        assert response.data['results'][0]['sku'] == 'LAPTOP-001'

    def test_search_sku_prefix_match(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'keyword': 'LAPTOP'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_search_inactive_excluded_by_default(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'keyword': 'keyboard'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_search_include_inactive_super_admin(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(
            reverse('inventory:search'), {'keyword': 'keyboard', 'include_inactive': 'true'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['sku'] == 'KEYBOARD-001'

    def test_search_include_inactive_non_admin_ignored(self, api_client, item_manager, items):
        api_client.force_authenticate(user=item_manager)
        response = api_client.get(
            reverse('inventory:search'), {'keyword': 'keyboard', 'include_inactive': 'true'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_search_item_manager_sees_all_active_inventory(self, api_client, item_manager, items):
        api_client.force_authenticate(user=item_manager)
        response = api_client.get(reverse('inventory:search'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
        assert {row['sku'] for row in response.data['results']} == {
            'LAPTOP-001', 'LAPTOP-002', 'MOUSE-001'
        }

    def test_search_filter_by_type(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'type': 'consumable'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['type'] == 'consumable'

    def test_search_filter_by_status(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'status': 'in_stock'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['status'] == 'in_stock'

    def test_search_filter_by_category(self, api_client, super_admin, items, category):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'category': category.id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_search_filter_by_location(self, api_client, super_admin, items, location):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'location': location.id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_search_combined_keyword_and_filter(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(
            reverse('inventory:search'), {'keyword': 'laptop', 'type': 'reusable'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_search_empty_keyword_stripped(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'keyword': '   '})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_search_pagination(self, api_client, super_admin, items):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(reverse('inventory:search'), {'page_size': 2})
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert len(response.data['results']) <= 2

    def test_search_read_only_user_can_search(self, api_client, read_only_user, items):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.get(reverse('inventory:search'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
