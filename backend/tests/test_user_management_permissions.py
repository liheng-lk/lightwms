"""Personnel administration acceptance tests."""
import pytest
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(
        username='people_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        username='people_manager', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def ordinary():
    return User.objects.create_user(
        username='people_user', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.mark.django_db
class TestCreateAndRoleManagement:
    def test_admin_create_defaults_to_ordinary_user(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            '/api/v1/users/create/',
            {'username': 'created_person', 'password': 'AnotherPass123!'},
            format='json',
        )
        assert response.status_code == 201
        assert response.data['role'] == UserRole.READ_ONLY_USER
        assert User.objects.get(username='created_person').role == UserRole.READ_ONLY_USER

    @pytest.mark.parametrize('fixture_name', ['manager', 'ordinary'])
    def test_non_admin_cannot_create_users(self, request, api_client, fixture_name):
        api_client.force_authenticate(user=request.getfixturevalue(fixture_name))
        response = api_client.post(
            '/api/v1/users/create/',
            {'username': f'forbidden_{fixture_name}', 'password': 'AnotherPass123!'},
            format='json',
        )
        assert response.status_code == 403

    def test_admin_can_promote_ordinary_user(self, api_client, admin, ordinary):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/v1/users/{ordinary.id}/update-role/',
            {'role': UserRole.ITEM_MANAGER},
            format='json',
        )
        assert response.status_code == 200
        ordinary.refresh_from_db()
        assert ordinary.role == UserRole.ITEM_MANAGER

    def test_admin_cannot_change_own_role(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/v1/users/{admin.id}/update-role/',
            {'role': UserRole.READ_ONLY_USER},
            format='json',
        )
        assert response.status_code == 400
        admin.refresh_from_db()
        assert admin.role == UserRole.SUPER_ADMIN

    def test_manager_cannot_change_roles(self, api_client, manager, ordinary):
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/users/{ordinary.id}/update-role/',
            {'role': UserRole.ITEM_MANAGER},
            format='json',
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestEnableDisable:
    def test_admin_can_disable_and_enable_user(self, api_client, admin, ordinary):
        api_client.force_authenticate(user=admin)
        disabled = api_client.post(f'/api/v1/users/{ordinary.id}/disable/')
        assert disabled.status_code == 200
        ordinary.refresh_from_db()
        assert ordinary.is_active is False
        assert ordinary.tokens_invalid_before is not None

        enabled = api_client.post(f'/api/v1/users/{ordinary.id}/enable/')
        assert enabled.status_code == 200
        ordinary.refresh_from_db()
        assert ordinary.is_active is True

    def test_admin_cannot_disable_self(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/v1/users/{admin.id}/disable/')
        assert response.status_code == 400
        admin.refresh_from_db()
        assert admin.is_active is True

    @pytest.mark.parametrize('fixture_name', ['manager', 'ordinary'])
    def test_non_admin_cannot_disable_users(self, request, api_client, fixture_name, ordinary):
        actor = request.getfixturevalue(fixture_name)
        target = ordinary
        if actor.id == target.id:
            target = User.objects.create_user(
                username='people_target', password='StrongPass123!', role=UserRole.READ_ONLY_USER
            )
        api_client.force_authenticate(user=actor)
        assert api_client.post(f'/api/v1/users/{target.id}/disable/').status_code == 403


@pytest.mark.django_db
class TestPasswordManagement:
    def test_ordinary_user_can_change_own_password(self, api_client, ordinary):
        api_client.force_authenticate(user=ordinary)
        response = api_client.post(
            '/api/v1/users/me/change-password/',
            {'old_password': 'StrongPass123!', 'new_password': 'NewStrongPass456!'},
            format='json',
        )
        assert response.status_code == 200
        ordinary.refresh_from_db()
        assert ordinary.check_password('NewStrongPass456!')

    def test_admin_can_reset_password_and_force_change(self, api_client, admin, ordinary):
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/v1/users/{ordinary.id}/reset-password/')
        assert response.status_code == 200
        assert response.data['must_change_password'] is True
        assert response.data['temporary_password']
        ordinary.refresh_from_db()
        assert ordinary.must_change_password is True
        assert ordinary.tokens_invalid_before is not None

    def test_manager_cannot_set_another_users_password(self, api_client, manager, ordinary):
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/users/{ordinary.id}/set-password/',
            {'new_password': 'AnotherPass456!'},
            format='json',
        )
        assert response.status_code == 403

    def test_weak_password_is_rejected(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            '/api/v1/users/create/',
            {'username': 'weak_person', 'password': '12345678'},
            format='json',
        )
        assert response.status_code == 400
        assert not User.objects.filter(username='weak_person').exists()
