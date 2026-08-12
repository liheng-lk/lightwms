"""Hardening tests for audit/login logs and system settings."""
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, LoginLog, TargetType
from apps.settings.models import SystemSettings
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='audit_settings_admin', password='StrongPass123!',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='audit_settings_manager', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='audit_settings_ordinary', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


def make_audit(operator, *, target_id=1):
    return AuditLog.objects.create(
        action=AuditAction.UPDATE,
        target_type=TargetType.ITEM,
        target_id=target_id,
        diff={'before': {'x': 1}, 'after': {'x': 2}},
        operator=operator,
        operator_role=operator.role,
        ip='127.0.0.1',
        user_agent='pytest',
    )


def make_login(user, *, success=True):
    return LoginLog.objects.create(
        username_attempted=user.username,
        user=user,
        success=success,
        ip='127.0.0.1',
        user_agent='pytest',
    )


@pytest.mark.django_db
class TestAuditQueryContract:
    @pytest.mark.parametrize('params', [
        {'operator_id': 'not-an-int'},
        {'operator_id': 9_223_372_036_854_775_808},
        {'action': 'not-an-action'},
        {'target_type': 'NotAType'},
        {'date_from': 'definitely-not-a-date'},
        {'date_to': '2026-99-99'},
        {'date_from': '2026-08-13', 'date_to': '2026-08-12'},
    ])
    def test_invalid_audit_filters_return_400(self, admin, params):
        make_audit(admin)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/audit-logs/', params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    @pytest.mark.parametrize('params', [
        {'user_id': 'not-an-int'},
        {'user_id': 9_223_372_036_854_775_808},
        {'success': 'maybe'},
        {'ip': '999.999.999.999'},
        {'date_from': 'bad-date'},
        {'date_from': '2026-08-13', 'date_to': '2026-08-12'},
    ])
    def test_invalid_login_log_filters_return_400(self, admin, params):
        make_login(admin)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/login-logs/', params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_invalid_resource_history_action_returns_400(self, admin):
        audit = make_audit(admin)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(
            f'/api/v1/audit-logs/resource/{TargetType.ITEM}/{audit.target_id}/',
            {'action': 'not-an-action'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_invalid_user_activity_target_type_returns_400(self, admin):
        make_audit(admin)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(
            f'/api/v1/audit-logs/user/{admin.id}/',
            {'target_type': 'NotAType'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
class TestAuditImmutability:
    def test_queryset_update_cannot_modify_audit_log(self, admin):
        audit = make_audit(admin)

        with pytest.raises(PermissionError):
            AuditLog.objects.filter(pk=audit.pk).update(action=AuditAction.DELETE)

        audit.refresh_from_db()
        assert audit.action == AuditAction.UPDATE

    def test_queryset_delete_cannot_remove_audit_log(self, admin):
        audit = make_audit(admin)

        with pytest.raises(PermissionError):
            AuditLog.objects.filter(pk=audit.pk).delete()

        assert AuditLog.objects.filter(pk=audit.pk).exists()

    def test_audit_target_id_supports_bigauto_range(self, admin):
        target_id = 5_000_000_000
        audit = make_audit(admin, target_id=target_id)
        audit.refresh_from_db()
        assert audit.target_id == target_id


@pytest.mark.django_db
class TestSettingsPermissionsAndAudit:
    def test_public_get_exposes_only_public_logo_setting(self):
        client = APIClient()
        response = client.get('/api/v1/system-settings/')

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data.keys()) == {'logo_url'}

    @pytest.mark.parametrize('role_fixture', ['manager', 'ordinary'])
    def test_non_superadmin_cannot_update_settings(self, request, role_fixture):
        user = request.getfixturevalue(role_fixture)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            '/api/v1/system-settings/',
            {'logo_url': 'https://example.com/logo.png'},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not SystemSettings.objects.filter(key=SystemSettings.LOGO_URL).exists()

    def test_superadmin_can_set_logo_url_and_system_audit_is_written(self, admin):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.put(
            '/api/v1/system-settings/',
            {'logo_url': 'https://example.com/logo.png'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['logo_url'] == 'https://example.com/logo.png'
        assert AuditLog.objects.filter(
            target_type=TargetType.SYSTEM,
            operator=admin,
        ).exists()

    @pytest.mark.parametrize('url', [
        'javascript:alert(1)',
        'data:image/svg+xml,<svg onload=alert(1)>',
        'file:///etc/passwd',
        'https://user:password@example.com/logo.png',
    ])
    def test_unsafe_logo_urls_are_rejected(self, admin, url):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.put('/api/v1/system-settings/', {'logo_url': url}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not SystemSettings.objects.filter(
            key=SystemSettings.LOGO_URL,
            value=url,
        ).exists()


@pytest.mark.django_db
class TestLogoFileLifecycle:
    def test_extension_spoofed_png_is_rejected_without_changing_settings(self, admin):
        client = APIClient()
        client.force_authenticate(user=admin)
        fake_png = SimpleUploadedFile(
            'logo.png', b'<script>alert(1)</script>', content_type='image/png'
        )

        response = client.post(
            '/api/v1/system-settings/upload-logo/',
            {'logo': fake_png},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert SystemSettings.objects.filter(key=SystemSettings.LOGO_FILE).count() == 0

    def test_active_svg_payload_is_rejected(self, admin):
        client = APIClient()
        client.force_authenticate(user=admin)
        active_svg = SimpleUploadedFile(
            'logo.svg',
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            content_type='image/svg+xml',
        )

        response = client.post(
            '/api/v1/system-settings/upload-logo/',
            {'logo': active_svg},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not SystemSettings.objects.filter(key=SystemSettings.LOGO_FILE).exists()

    def test_valid_logo_upload_writes_system_audit_and_file(self, admin):
        # Minimal valid 1x1 PNG.
        png = bytes.fromhex(
            '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
            '0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082'
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            '/api/v1/system-settings/upload-logo/',
            {'logo': SimpleUploadedFile('logo.png', png, content_type='image/png')},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        relative = SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value
        path = Path(settings.MEDIA_ROOT) / relative
        try:
            assert path.exists()
            assert response.data['logo_url'] == f'/media/{relative}'
            assert AuditLog.objects.filter(
                target_type=TargetType.SYSTEM,
                operator=admin,
            ).exists()
        finally:
            path.unlink(missing_ok=True)
