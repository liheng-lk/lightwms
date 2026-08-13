"""Transactional filesystem lifecycle tests for system logo changes."""
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.settings.models import SystemSettings
from apps.settings.services import SystemSettingsService
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='logo_tx_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


def png_bytes(rgb):
    output = BytesIO()
    Image.new('RGB', (2, 2), rgb).save(output, format='PNG')
    return output.getvalue()


def upload(client, name, content):
    return client.post(
        '/api/v1/system-settings/upload-logo/',
        {'logo': SimpleUploadedFile(name, content, content_type='image/png')},
        format='multipart',
    )


@pytest.mark.django_db
class TestLogoReplacementLifecycle:
    def test_replacement_deletes_old_file_only_after_commit(
        self, admin, tmp_path, django_capture_on_commit_callbacks,
    ):
        client = APIClient()
        client.force_authenticate(user=admin)

        with override_settings(MEDIA_ROOT=str(tmp_path)):
            first = upload(client, 'first.png', png_bytes((255, 0, 0)))
            assert first.status_code == status.HTTP_200_OK
            first_relative = SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value
            first_path = tmp_path / first_relative
            assert first_path.exists()

            with django_capture_on_commit_callbacks(execute=True):
                second = upload(client, 'second.png', png_bytes((0, 255, 0)))

            assert second.status_code == status.HTTP_200_OK
            second_relative = SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value
            second_path = tmp_path / second_relative
            assert second_relative != first_relative
            assert second_path.exists()
            assert not first_path.exists()

    def test_switching_to_remote_url_removes_uploaded_file_after_commit(
        self, admin, tmp_path, django_capture_on_commit_callbacks,
    ):
        client = APIClient()
        client.force_authenticate(user=admin)

        with override_settings(MEDIA_ROOT=str(tmp_path)):
            created = upload(client, 'local.png', png_bytes((0, 0, 255)))
            assert created.status_code == status.HTTP_200_OK
            relative = SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value
            path = tmp_path / relative
            assert path.exists()

            with django_capture_on_commit_callbacks(execute=True):
                response = client.put(
                    '/api/v1/system-settings/',
                    {'logo_url': 'https://static.example.com/logo.png'},
                    format='json',
                )

            assert response.status_code == status.HTTP_200_OK
            assert response.data['logo_url'] == 'https://static.example.com/logo.png'
            assert SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value == ''
            assert not path.exists()

    def test_audit_failure_rolls_back_setting_and_removes_new_file_but_keeps_old(
        self, admin, tmp_path, monkeypatch,
    ):
        old_relative = 'system/logo_existing.png'
        old_path = tmp_path / old_relative
        old_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_bytes(png_bytes((10, 10, 10)))
        SystemSettings.objects.create(
            key=SystemSettings.LOGO_FILE,
            value=old_relative,
            updated_by=admin,
        )
        SystemSettings.objects.create(
            key=SystemSettings.LOGO_URL,
            value='',
            updated_by=admin,
        )

        def fail_audit(*args, **kwargs):
            raise RuntimeError('simulated audit failure')

        monkeypatch.setattr(AuditLog.objects, 'create', fail_audit)

        with override_settings(MEDIA_ROOT=str(tmp_path)):
            with pytest.raises(RuntimeError, match='simulated audit failure'):
                SystemSettingsService.upload_logo(
                    SimpleUploadedFile(
                        'replacement.png',
                        png_bytes((20, 20, 20)),
                        content_type='image/png',
                    ),
                    operator=admin,
                )

        assert SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value == old_relative
        assert old_path.exists()
        assert list((tmp_path / 'system').glob('logo_*.png')) == [old_path]


@pytest.mark.django_db
def test_unsafe_legacy_logo_file_path_is_not_reflected(admin, tmp_path):
    SystemSettings.objects.create(
        key=SystemSettings.LOGO_FILE,
        value='../outside.png',
        updated_by=admin,
    )
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        assert SystemSettingsService.get_logo_url() is None
