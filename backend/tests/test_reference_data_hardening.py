"""Regression tests for warehouse, location and category reference data."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Category, Location, Warehouse
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='reference_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='reference_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='reference_other_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='reference_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='REF-WH', name='Reference Warehouse', is_active=True)


@pytest.mark.django_db
class TestInactiveReferenceVisibility:
    @pytest.mark.parametrize('role_fixture', ['manager', 'ordinary'])
    def test_non_superadmin_cannot_open_inactive_warehouse_by_id(
        self, request, api_client, role_fixture
    ):
        user = request.getfixturevalue(role_fixture)
        warehouse = Warehouse.objects.create(
            code=f'INACTIVE-WH-{role_fixture}', name='Inactive Warehouse', is_active=False
        )
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/v1/warehouses/{warehouse.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize('role_fixture', ['manager', 'ordinary'])
    def test_non_superadmin_cannot_open_inactive_location_by_id(
        self, request, api_client, role_fixture, warehouse, manager
    ):
        user = request.getfixturevalue(role_fixture)
        location = Location.objects.create(
            warehouse=warehouse, code=f'INACTIVE-LOC-{role_fixture}',
            name='Inactive Location', owner=manager, is_active=False,
        )
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/v1/locations/{location.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize('role_fixture', ['manager', 'ordinary'])
    def test_non_superadmin_cannot_open_inactive_category_by_id(
        self, request, api_client, role_fixture
    ):
        user = request.getfixturevalue(role_fixture)
        category = Category.objects.create(
            name=f'Inactive Category {role_fixture}', is_active=False
        )
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/v1/categories/{category.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_superadmin_can_open_inactive_reference_records(
        self, api_client, admin, manager, warehouse
    ):
        inactive_warehouse = Warehouse.objects.create(
            code='INACTIVE-WH-ADMIN', name='Inactive admin warehouse', is_active=False
        )
        inactive_location = Location.objects.create(
            warehouse=warehouse, code='INACTIVE-LOC-ADMIN',
            name='Inactive admin location', owner=manager, is_active=False,
        )
        inactive_category = Category.objects.create(
            name='Inactive Category Admin', is_active=False
        )
        api_client.force_authenticate(user=admin)
        assert api_client.get(f'/api/v1/warehouses/{inactive_warehouse.id}/').status_code == 200
        assert api_client.get(f'/api/v1/locations/{inactive_location.id}/').status_code == 200
        assert api_client.get(f'/api/v1/categories/{inactive_category.id}/').status_code == 200


@pytest.mark.django_db
class TestWarehouseLocationVisibility:
    def test_locations_in_inactive_warehouse_are_hidden_from_default_list(
        self, api_client, ordinary, manager
    ):
        warehouse = Warehouse.objects.create(
            code='REF-INACTIVE-WH-LIST', name='Inactive parent', is_active=False
        )
        location = Location.objects.create(
            warehouse=warehouse, code='REF-HIDDEN-LOC', name='Hidden Location',
            owner=manager, is_active=True,
        )
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/locations/')
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert location.id not in ids

    def test_locations_in_inactive_warehouse_are_hidden_from_default_tree(
        self, api_client, ordinary, manager
    ):
        warehouse = Warehouse.objects.create(
            code='REF-INACTIVE-WH-TREE', name='Inactive tree parent', is_active=False
        )
        location = Location.objects.create(
            warehouse=warehouse, code='REF-HIDDEN-TREE-LOC', name='Hidden Tree Location',
            owner=manager, is_active=True,
        )
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/locations/tree/')
        assert response.status_code == status.HTTP_200_OK

        def flatten(nodes):
            result = []
            for node in nodes:
                result.append(node['id'])
                result.extend(flatten(node.get('children', [])))
            return result

        assert location.id not in flatten(response.data)


@pytest.mark.django_db
class TestLocationHierarchyAndOwnerRules:
    def test_location_cannot_be_created_under_inactive_parent(
        self, api_client, manager, warehouse
    ):
        parent = Location.objects.create(
            warehouse=warehouse, code='REF-INACTIVE-PARENT', name='Inactive Parent',
            owner=manager, is_active=False,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/locations/', {
            'warehouse': warehouse.id,
            'code': 'REF-CHILD-BLOCKED',
            'name': 'Blocked Child',
            'owner': manager.id,
            'parent': parent.id,
        }, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert not Location.objects.filter(code='REF-CHILD-BLOCKED').exists()

    def test_location_cannot_be_owned_by_ordinary_user(
        self, api_client, manager, ordinary, warehouse
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/locations/', {
            'warehouse': warehouse.id,
            'code': 'REF-BAD-OWNER',
            'name': 'Bad Owner',
            'owner': ordinary.id,
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Location.objects.filter(code='REF-BAD-OWNER').exists()

    def test_manager_cannot_assign_new_location_to_another_manager(
        self, api_client, manager, other_manager, warehouse
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/locations/', {
            'warehouse': warehouse.id,
            'code': 'REF-CROSS-OWNER',
            'name': 'Cross Owner',
            'owner': other_manager.id,
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Location.objects.filter(code='REF-CROSS-OWNER').exists()

    def test_manager_cannot_reassign_location_to_ordinary_user(
        self, api_client, manager, ordinary, warehouse
    ):
        location = Location.objects.create(
            warehouse=warehouse, code='REF-OWNER-UPDATE', name='Owner Update',
            owner=manager, is_active=True,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.patch(
            f'/api/v1/locations/{location.id}/', {'owner': ordinary.id}, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        location.refresh_from_db()
        assert location.owner_id == manager.id


@pytest.mark.django_db
class TestCategoryHierarchyRules:
    def test_category_cannot_be_created_under_inactive_parent(
        self, api_client, manager
    ):
        parent = Category.objects.create(name='Inactive Category Parent', is_active=False)
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/categories/', {
            'name': 'Blocked Category Child',
            'parent': parent.id,
        }, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert not Category.objects.filter(name='Blocked Category Child').exists()
