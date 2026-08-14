"""Regression tests for the LightWMS personnel permission matrix."""
from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import InviteCode, User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        username='perm_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        username='perm_manager', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def other_manager():
    return User.objects.create_user(
        username='perm_manager_2', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def ordinary_user():
    return User.objects.create_user(
        username='perm_user', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        username='perm_user_2', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.fixture
def warehouse():
    return Warehouse.objects.create(code='PERM-WH', name='Permission Warehouse')


@pytest.fixture
def location(warehouse):
    return Location.objects.create(
        warehouse=warehouse, code='PERM-L01', name='Permission Location'
    )


@pytest.fixture
def manager_item(location, manager):
    return Item.objects.create(
        name='Manager Reusable',
        sku='PERM-R-001',
        location=location,
        owner=manager,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        quantity=1,
    )


@pytest.fixture
def other_manager_item(location, other_manager):
    return Item.objects.create(
        name='Other Manager Reusable',
        sku='PERM-R-002',
        location=location,
        owner=other_manager,
        type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE,
        quantity=1,
    )


@pytest.mark.django_db
class TestRoleDefaults:
    def test_regular_user_defaults_to_ordinary_role(self):
        user = User.objects.create_user(username='default_user', password='StrongPass123!')
        assert user.role == UserRole.READ_ONLY_USER

    def test_invite_code_defaults_to_ordinary_role(self, super_admin):
        code = InviteCode.objects.create(code='INV-PERM01', created_by=super_admin)
        assert code.default_role == UserRole.READ_ONLY_USER

    def test_legacy_builtin_invite_code_is_not_a_bypass(self, api_client):
        response = api_client.post(
            '/api/v1/auth/register/',
            {
                'invite_code': 'hdu340',
                'username': 'bypass_attempt',
                'password': 'StrongPass123!',
            },
            format='json',
        )
        assert response.status_code == 400
        assert not User.objects.filter(username='bypass_attempt').exists()


@pytest.mark.django_db
class TestSystemAdministrationBoundary:
    def test_super_admin_can_list_users(self, api_client, super_admin):
        api_client.force_authenticate(user=super_admin)
        assert api_client.get('/api/v1/users/').status_code == 200

    @pytest.mark.parametrize('fixture_name', ['manager', 'ordinary_user'])
    def test_non_admin_cannot_list_users(self, request, api_client, fixture_name):
        user = request.getfixturevalue(fixture_name)
        api_client.force_authenticate(user=user)
        assert api_client.get('/api/v1/users/').status_code == 403

    def test_manager_cannot_create_invite_code(self, api_client, manager):
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/invite-codes/', {'max_uses': 1}, format='json')
        assert response.status_code == 403


@pytest.mark.django_db
class TestInventoryBoundary:
    def test_ordinary_user_can_read_inventory(self, api_client, ordinary_user, manager_item):
        api_client.force_authenticate(user=ordinary_user)
        response = api_client.get('/api/v1/items/')
        assert response.status_code == 200

    def test_manager_lists_inventory_across_owners(
        self, api_client, manager, manager_item, other_manager_item
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/items/', {'page_size': 100})
        assert response.status_code == 200
        rows = response.data.get('results', response.data)
        ids = {row['id'] for row in rows}
        assert manager_item.id in ids
        assert other_manager_item.id in ids

    def test_ordinary_user_cannot_create_inventory(self, api_client, ordinary_user, location):
        api_client.force_authenticate(user=ordinary_user)
        response = api_client.post(
            '/api/v1/items/',
            {
                'name': 'Forbidden Create',
                'sku': 'PERM-FORBIDDEN',
                'location': location.id,
                'type': 'reusable',
                'quantity': 1,
            },
            format='json',
        )
        assert response.status_code == 403

    def test_manager_can_update_another_managers_item(
        self, api_client, manager, other_manager_item
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.patch(
            f'/api/v1/items/{other_manager_item.id}/',
            {'name': 'Globally Managed'},
            format='json',
        )
        assert response.status_code == 200
        other_manager_item.refresh_from_db()
        assert other_manager_item.name == 'Globally Managed'


@pytest.mark.django_db
class TestOperationBoundary:
    def test_ordinary_user_cannot_register_borrow(
        self, api_client, ordinary_user, manager_item
    ):
        api_client.force_authenticate(user=ordinary_user)
        response = api_client.post(
            f'/api/v1/items/{manager_item.id}/borrow/',
            {
                'borrower': ordinary_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json',
        )
        assert response.status_code == 403

    def test_manager_can_borrow_owned_item_for_user(
        self, api_client, manager, ordinary_user, manager_item
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{manager_item.id}/borrow/',
            {
                'borrower': ordinary_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json',
        )
        assert response.status_code == 201

    def test_manager_can_borrow_other_managers_item(
        self, api_client, manager, ordinary_user, other_manager_item
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{other_manager_item.id}/borrow/',
            {
                'borrower': ordinary_user.id,
                'expected_return_date': (date.today() + timedelta(days=7)).isoformat(),
            },
            format='json',
        )
        assert response.status_code == 201

    def test_borrower_can_return_own_borrow(
        self, api_client, manager, ordinary_user, manager_item
    ):
        BorrowRecord.objects.create(
            item=manager_item,
            borrower=ordinary_user,
            operator=manager,
            expected_return_date=date.today() + timedelta(days=7),
            status=BorrowStatus.ACTIVE,
        )
        manager_item.status = ItemStatus.BORROWED
        manager_item.save(update_fields=['status'])

        api_client.force_authenticate(user=ordinary_user)
        response = api_client.post(
            f'/api/v1/items/{manager_item.id}/return/',
            {'return_notes': 'self return'},
            format='json',
        )
        assert response.status_code == 200

    def test_ordinary_user_sees_only_own_borrow_records(
        self, api_client, manager, ordinary_user, other_user, manager_item, other_manager_item
    ):
        BorrowRecord.objects.create(
            item=manager_item,
            borrower=ordinary_user,
            operator=manager,
            expected_return_date=date.today() + timedelta(days=7),
            status=BorrowStatus.ACTIVE,
        )
        BorrowRecord.objects.create(
            item=other_manager_item,
            borrower=other_user,
            operator=manager,
            expected_return_date=date.today() + timedelta(days=7),
            status=BorrowStatus.ACTIVE,
        )

        api_client.force_authenticate(user=ordinary_user)
        response = api_client.get('/api/v1/borrow-records/')
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        assert len(results) == 1
        assert results[0]['borrower'] == ordinary_user.id
