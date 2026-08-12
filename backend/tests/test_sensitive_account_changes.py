"""Session invalidation tests for security-sensitive account changes."""
import pytest
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(
        username='session_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def user():
    return User.objects.create_user(
        username='session_user', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.mark.django_db
class TestSensitiveChangesInvalidateSessions:
    def test_role_change_invalidates_existing_sessions(self, api_client, admin, user):
        assert user.tokens_invalid_before is None
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/v1/users/{user.id}/update-role/',
            {'role': UserRole.ITEM_MANAGER},
            format='json',
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.tokens_invalid_before is not None

    def test_admin_set_password_invalidates_existing_sessions(self, api_client, admin, user):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/v1/users/{user.id}/set-password/',
            {'new_password': 'ChangedByAdmin456!'},
            format='json',
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.tokens_invalid_before is not None

    def test_self_password_change_invalidates_existing_sessions(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            '/api/v1/users/me/change-password/',
            {
                'old_password': 'StrongPass123!',
                'new_password': 'ChangedBySelf456!',
            },
            format='json',
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.tokens_invalid_before is not None
