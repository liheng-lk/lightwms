"""Sensitive data must never be persisted or exposed through audit APIs."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.audit.sanitization import REDACTED
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='audit_sensitive_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
class TestAuditWriteSanitization:
    def test_direct_create_recursively_redacts_sensitive_values(self, admin):
        audit = AuditLog.objects.create(
            action=AuditAction.UPDATE,
            target_type=TargetType.USER,
            target_id=admin.id,
            diff={
                'before': {
                    'profile': {
                        'password': 'old-secret',
                        'normal': 'keep-me',
                    },
                    'authorization': 'Bearer secret',
                },
                'after': {
                    'items': [
                        {'access_token': 'token-a'},
                        {'api-key': 'token-b'},
                    ],
                    'refresh_token': 'refresh-secret',
                },
            },
            operator=admin,
            operator_role=admin.role,
        )

        audit.refresh_from_db()
        assert audit.diff['before']['profile']['password'] == REDACTED
        assert audit.diff['before']['profile']['normal'] == 'keep-me'
        assert audit.diff['before']['authorization'] == REDACTED
        assert audit.diff['after']['items'][0]['access_token'] == REDACTED
        assert audit.diff['after']['items'][1]['api-key'] == REDACTED
        assert audit.diff['after']['refresh_token'] == REDACTED
        serialized = str(audit.diff)
        assert 'old-secret' not in serialized
        assert 'token-a' not in serialized
        assert 'token-b' not in serialized
        assert 'refresh-secret' not in serialized


@pytest.mark.django_db
class TestAuditReadSanitization:
    def test_api_masks_legacy_row_inserted_without_model_save(self, admin):
        # bulk_create bypasses Model.save and simulates a legacy/direct DB row.
        AuditLog.objects.bulk_create([
            AuditLog(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=admin.id,
                diff={
                    'after': {
                        'nested': {'client_secret': 'historic-secret'},
                        'cookie': 'session=historic',
                        'safe': 'visible',
                    }
                },
                operator=admin,
                operator_role=admin.role,
            )
        ])
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/audit-logs/', {'target_type': TargetType.USER})

        assert response.status_code == status.HTTP_200_OK
        row = response.data['results'][0]
        assert row['diff']['after']['nested']['client_secret'] == REDACTED
        assert row['diff']['after']['cookie'] == REDACTED
        assert row['diff']['after']['safe'] == 'visible'
        assert 'historic-secret' not in str(row['diff'])
        assert 'session=historic' not in str(row['diff'])
