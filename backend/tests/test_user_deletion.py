"""Regression tests for history-safe user deletion."""
import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Location, Warehouse
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(
        username='delete_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        username='delete_manager', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def target():
    return User.objects.create_user(
        username='delete_target', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


@pytest.mark.django_db
class TestUserDeletion:
    def test_super_admin_can_delete_unreferenced_user_and_audit_it(self, api_client, admin, target):
        target_id = target.id
        api_client.force_authenticate(user=admin)

        response = api_client.delete(f'/api/v1/users/{target_id}/')

        assert response.status_code == 204
        assert not User.objects.filter(pk=target_id).exists()
        assert not User.all_objects.filter(pk=target_id).exists()
        audit = AuditLog.objects.get(
            action=AuditAction.DELETE,
            target_type=TargetType.USER,
            target_id=target_id,
        )
        assert audit.operator_id == admin.id
        assert audit.diff['before']['username'] == 'delete_target'
        assert audit.diff['after'] is None

    def test_non_super_admin_cannot_delete_user(self, api_client, manager, target):
        api_client.force_authenticate(user=manager)

        response = api_client.delete(f'/api/v1/users/{target.id}/')

        assert response.status_code == 403
        assert User.objects.filter(pk=target.id).exists()

    def test_super_admin_cannot_delete_self(self, api_client, admin):
        api_client.force_authenticate(user=admin)

        response = api_client.delete(f'/api/v1/users/{admin.id}/')

        assert response.status_code == 400
        assert response.data['code'] == 'INVALID_OPERATION'
        assert User.objects.filter(pk=admin.id).exists()

    def test_delete_missing_user_returns_404(self, api_client, admin):
        api_client.force_authenticate(user=admin)

        response = api_client.delete('/api/v1/users/999999999/')

        assert response.status_code == 404
        assert response.data['code'] == 'NOT_FOUND'

    def test_business_reference_is_archived_without_losing_history(self, api_client, admin, target):
        warehouse = Warehouse.objects.create(code='DEL-WH', name='Delete Guard Warehouse')
        location = Location.objects.create(
            warehouse=warehouse,
            code='DEL-LOC',
            name='Delete Guard Location',
            owner=target,
        )
        target_id = target.id
        api_client.force_authenticate(user=admin)

        response = api_client.delete(f'/api/v1/users/{target_id}/')

        assert response.status_code == 204
        assert not User.objects.filter(pk=target_id).exists()
        archived = User.all_objects.get(pk=target_id)
        assert archived.is_active is False
        assert archived.deleted_at is not None
        assert archived.tokens_invalid_before is not None
        assert archived.phone is None
        assert archived.wechat_openid is None
        assert not archived.has_usable_password()
        assert Location.objects.filter(pk=location.id, owner_id=target_id).exists()

        audit = AuditLog.objects.get(
            action=AuditAction.DELETE,
            target_type=TargetType.USER,
            target_id=target_id,
        )
        assert audit.diff['before']['username'] == 'delete_target'
        assert audit.diff['after']['archived'] is True
