"""Lifecycle integrity tests for warehouses, locations and categories."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Category, Item, ItemStatus, ItemType, Location, Warehouse
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='lifecycle_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='lifecycle_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='LIFE-WH', name='Lifecycle Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='LIFE-LOC', name='Lifecycle Location',
        owner=manager, is_active=True,
    )


def make_item(*, owner, location, sku, category=None, active=True):
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location, category=category,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=1, is_active=active,
    )


@pytest.mark.django_db
class TestWarehouseLifecycle:
    def test_deactivating_warehouse_preserves_children_but_hides_them_by_default(
        self, api_client, manager, warehouse, location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/warehouses/{warehouse.id}/deactivate/')
        assert response.status_code == status.HTTP_200_OK
        location.refresh_from_db()
        assert location.is_active is True

        response = api_client.get('/api/v1/locations/')
        ids = {row['id'] for row in response.data['results']}
        assert location.id not in ids

    def test_hard_delete_warehouse_is_blocked_even_by_inactive_location(
        self, api_client, admin, warehouse, location
    ):
        location.is_active = False
        location.save(update_fields=['is_active'])
        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/v1/warehouses/{warehouse.id}/delete/')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert Warehouse.objects.filter(id=warehouse.id).exists()


@pytest.mark.django_db
class TestLocationLifecycle:
    def test_deactivate_location_blocked_by_active_child(
        self, api_client, manager, warehouse, location
    ):
        Location.objects.create(
            warehouse=warehouse, parent=location, code='LIFE-CHILD',
            name='Child', owner=manager, is_active=True,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/locations/{location.id}/deactivate/')
        assert response.status_code == status.HTTP_409_CONFLICT
        location.refresh_from_db()
        assert location.is_active is True

    def test_deactivate_location_blocked_by_inactive_item_history(
        self, api_client, manager, location
    ):
        make_item(owner=manager, location=location, sku='LIFE-INACTIVE-ITEM', active=False)
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/locations/{location.id}/deactivate/')
        assert response.status_code == status.HTTP_409_CONFLICT
        location.refresh_from_db()
        assert location.is_active is True


@pytest.mark.django_db
class TestCategoryLifecycle:
    def test_deactivate_category_blocked_by_inactive_child(
        self, api_client, manager
    ):
        parent = Category.objects.create(name='Lifecycle Parent', is_active=True)
        Category.objects.create(name='Lifecycle Inactive Child', parent=parent, is_active=False)
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/categories/{parent.id}/deactivate/')
        assert response.status_code == status.HTTP_409_CONFLICT
        parent.refresh_from_db()
        assert parent.is_active is True

    def test_deactivate_category_blocked_by_inactive_item_history(
        self, api_client, manager, location
    ):
        category = Category.objects.create(name='Lifecycle Item Category', is_active=True)
        make_item(
            owner=manager, location=location, sku='LIFE-CATEGORY-ITEM',
            category=category, active=False,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/categories/{category.id}/deactivate/')
        assert response.status_code == status.HTTP_409_CONFLICT
        category.refresh_from_db()
        assert category.is_active is True
