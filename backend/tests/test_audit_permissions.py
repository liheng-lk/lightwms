"""Audit visibility permission tests."""
import pytest
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(
        username='audit_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        username='audit_manager', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def ordinary():
    return User.objects.create_user(
        username='audit_user', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.mark.django_db
class TestAuditPermissions:
    def test_super_admin_can_view_audit_logs(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        assert api_client.get('/api/v1/audit-logs/').status_code == 200

    @pytest.mark.parametrize('fixture_name', ['manager', 'ordinary'])
    def test_non_admin_cannot_view_audit_logs(self, request, api_client, fixture_name):
        api_client.force_authenticate(user=request.getfixturevalue(fixture_name))
        assert api_client.get('/api/v1/audit-logs/').status_code == 403

    def test_manager_cannot_view_login_logs(self, api_client, manager):
        api_client.force_authenticate(user=manager)
        assert api_client.get('/api/v1/login-logs/').status_code == 403
