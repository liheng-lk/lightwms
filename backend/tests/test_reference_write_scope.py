"""Write-scope tests for global inventory-manager locations."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Location, Warehouse
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='scope_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='scope_other_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='SCOPE-WH', name='Scope Warehouse', is_active=True)


@pytest.fixture
def other_location(db, warehouse, other_manager):
    return Location.objects.create(
        warehouse=warehouse, code='SCOPE-OTHER', name='Other Location',
        owner=other_manager, is_active=True,
    )


@pytest.mark.django_db
class TestManagerLocationWriteScope:
    def test_manager_can_patch_other_managers_location(
        self, api_client, manager, other_location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.patch(
            f'/api/v1/locations/{other_location.id}/',
            {'name': 'Managed Globally'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        other_location.refresh_from_db()
        assert other_location.name == 'Managed Globally'

    def test_manager_can_reassign_other_managers_location_to_self(
        self, api_client, manager, other_location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.patch(
            f'/api/v1/locations/{other_location.id}/',
            {'owner': manager.id},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        other_location.refresh_from_db()
        assert other_location.owner_id == manager.id

    def test_manager_can_deactivate_other_managers_location(
        self, api_client, manager, other_location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/locations/{other_location.id}/deactivate/')
        assert response.status_code == status.HTTP_200_OK
        other_location.refresh_from_db()
        assert other_location.is_active is False
