"""Tests for Item API endpoints and the inventory role contract."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Category, Item, ItemStatus, ItemType, Location, Warehouse
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin(db):
    return User.objects.create_user(
        username='superadmin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def item_manager(db):
    return User.objects.create_user(
        username='itemmanager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def read_only_user(db):
    return User.objects.create_user(
        username='readonly', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='WH-001', name='Test Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse):
    return Location.objects.create(
        warehouse=warehouse, code='LOC-001', name='Test Location', is_active=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name='Test Category', is_active=True)


@pytest.fixture
def reusable_item(db, location, category, item_manager):
    return Item.objects.create(
        name='Test Reusable Item', sku='SKU-001', location=location,
        category=category, owner=item_manager, type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE, is_active=True,
    )


@pytest.fixture
def consumable_item(db, location, category, item_manager):
    return Item.objects.create(
        name='Test Consumable Item', sku='SKU-002', location=location,
        category=category, owner=item_manager, type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK, quantity=100, is_active=True,
    )


def _other_item(location, category, owner, sku):
    return Item.objects.create(
        name=f'Item {sku}', sku=sku, location=location, category=category,
        owner=owner, type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        is_active=True,
    )


@pytest.mark.django_db
class TestItemListEndpoint:
    def test_list_items_authenticated(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1

    def test_list_items_unauthenticated(self, api_client, reusable_item):
        assert api_client.get('/api/v1/items/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_item_manager_lists_all_active_inventory(
        self, api_client, item_manager, super_admin, location, category
    ):
        own = _other_item(location, category, item_manager, 'SKU-MGR-001')
        admin_owned = _other_item(location, category, super_admin, 'SKU-ADM-001')
        api_client.force_authenticate(user=item_manager)
        response = api_client.get('/api/v1/items/', {'page_size': 100})
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert {own.id, admin_owned.id}.issubset(ids)

    def test_list_items_filter_by_type(
        self, api_client, super_admin, reusable_item, consumable_item
    ):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/', {'type': 'reusable'})
        assert response.status_code == status.HTTP_200_OK
        assert all(row['type'] == 'reusable' for row in response.data['results'])

    def test_list_items_filter_by_status(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/v1/items/', {'status': 'available'})
        assert response.status_code == status.HTTP_200_OK
        assert all(row['status'] == 'available' for row in response.data['results'])


@pytest.mark.django_db
class TestItemCreateEndpoint:
    def test_create_reusable_item(self, api_client, super_admin, location, category):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'New Reusable Item', 'sku': 'SKU-NEW-001',
            'location': location.id, 'category': category.id, 'type': 'reusable',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Reusable Item'
        assert response.data['sku'] == 'SKU-NEW-001'
        assert response.data['type'] == 'reusable'
        assert response.data['status'] == 'available'

    def test_create_consumable_item(self, api_client, super_admin, location, category):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'New Consumable Item', 'sku': 'SKU-NEW-002',
            'location': location.id, 'category': category.id,
            'type': 'consumable', 'quantity': 50,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['type'] == 'consumable'
        assert response.data['status'] == 'in_stock'
        assert response.data['quantity'] == 50

    def test_create_consumable_item_zero_quantity(
        self, api_client, super_admin, location, category
    ):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'Empty Consumable Item', 'sku': 'SKU-NEW-003',
            'location': location.id, 'category': category.id,
            'type': 'consumable', 'quantity': 0,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'out_of_stock'

    def test_create_item_default_owner(self, api_client, item_manager, location, category):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post('/api/v1/items/', {
            'name': 'Item Without Owner', 'sku': 'SKU-NEW-004',
            'location': location.id, 'type': 'reusable',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['owner'] == item_manager.id

    def test_create_item_duplicate_sku(
        self, api_client, super_admin, location, reusable_item
    ):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'Duplicate SKU Item', 'sku': reusable_item.sku,
            'location': location.id, 'type': 'reusable',
        })
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] in ('DUPLICATE_SKU', 'INTEGRITY_ERROR')

    def test_create_item_read_only_user_forbidden(
        self, api_client, read_only_user, location
    ):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post('/api/v1/items/', {
            'name': 'Forbidden Item', 'sku': 'SKU-FORBIDDEN',
            'location': location.id, 'type': 'reusable',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestItemDetailEndpoint:
    def test_get_item_detail(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f'/api/v1/items/{reusable_item.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == reusable_item.id
        assert response.data['name'] == reusable_item.name

    def test_get_item_not_found(self, api_client, super_admin):
        api_client.force_authenticate(user=super_admin)
        assert api_client.get('/api/v1/items/99999/').status_code == status.HTTP_404_NOT_FOUND

    def test_item_manager_can_open_other_owner_item(
        self, api_client, item_manager, super_admin, location, category
    ):
        other_item = _other_item(location, category, super_admin, 'SKU-OTHER-001')
        api_client.force_authenticate(user=item_manager)
        response = api_client.get(f'/api/v1/items/{other_item.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == other_item.id


@pytest.mark.django_db
class TestItemUpdateEndpoint:
    def test_update_item(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.patch(
            f'/api/v1/items/{reusable_item.id}/', {'name': 'Updated Item Name'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Item Name'

    def test_update_item_owner_can_update(self, api_client, item_manager, reusable_item):
        api_client.force_authenticate(user=item_manager)
        response = api_client.patch(
            f'/api/v1/items/{reusable_item.id}/', {'name': 'Owner Updated Name'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Owner Updated Name'

    def test_item_manager_can_update_other_owner_item(
        self, api_client, location, category
    ):
        owner = User.objects.create_user(
            username='othermanager', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        operator = User.objects.create_user(
            username='nonowner', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        item = _other_item(location, category, owner, 'SKU-OTHER-MGR')
        api_client.force_authenticate(user=operator)
        response = api_client.patch(
            f'/api/v1/items/{item.id}/', {'name': 'Global Manager Update'}
        )
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.name == 'Global Manager Update'

    def test_update_item_read_only_user_forbidden(
        self, api_client, read_only_user, reusable_item
    ):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.patch(
            f'/api/v1/items/{reusable_item.id}/', {'name': 'Forbidden Update'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestItemDeactivateEndpoint:
    def test_deactivate_item(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_active'] is False

    def test_deactivate_item_owner_can_deactivate(
        self, api_client, item_manager, reusable_item
    ):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_active'] is False

    def test_item_manager_can_deactivate_other_owner_item(
        self, api_client, location, category
    ):
        owner = User.objects.create_user(
            username='othermanager2', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        operator = User.objects.create_user(
            username='nonowner2', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        item = _other_item(location, category, owner, 'SKU-OTHER-MGR-2')
        api_client.force_authenticate(user=operator)
        response = api_client.post(f'/api/v1/items/{item.id}/deactivate/')
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.is_active is False

    def test_deactivate_item_read_only_user_forbidden(
        self, api_client, read_only_user, reusable_item
    ):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/deactivate/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestItemGenerateBarcodeEndpoint:
    def test_generate_barcode(self, api_client, super_admin, reusable_item):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        assert response.status_code == status.HTTP_200_OK
        assert 'barcode' in response.data
        assert 'label_png_base64' in response.data
        assert response.data['barcode'].startswith('BC')

    def test_generate_barcode_owner_can_generate(
        self, api_client, item_manager, reusable_item
    ):
        api_client.force_authenticate(user=item_manager)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        assert response.status_code == status.HTTP_200_OK
        assert 'barcode' in response.data

    def test_item_manager_can_generate_barcode_for_other_owner_item(
        self, api_client, location, category
    ):
        owner = User.objects.create_user(
            username='othermanager3', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        operator = User.objects.create_user(
            username='nonowner3', password='testpass123',
            role=UserRole.ITEM_MANAGER, is_active=True,
        )
        item = _other_item(location, category, owner, 'SKU-OTHER-MGR-3')
        api_client.force_authenticate(user=operator)
        response = api_client.post(f'/api/v1/items/{item.id}/generate-barcode/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['barcode']

    def test_generate_barcode_read_only_user_forbidden(
        self, api_client, read_only_user, reusable_item
    ):
        api_client.force_authenticate(user=read_only_user)
        response = api_client.post(f'/api/v1/items/{reusable_item.id}/generate-barcode/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
