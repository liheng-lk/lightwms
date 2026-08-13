"""Positive/negative safety contract for uploaded SVG logos."""
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.settings.models import SystemSettings
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='safe_svg_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
def test_safe_inline_svg_logo_is_still_supported(admin, tmp_path):
    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">
      <defs><linearGradient id="g"><stop offset="0" stop-color="#111"/><stop offset="1" stop-color="#777"/></linearGradient></defs>
      <rect width="120" height="40" rx="6" fill="url(#g)"/>
      <path d="M10 20h20" stroke="#fff" stroke-width="2"/>
    </svg>'''
    client = APIClient()
    client.force_authenticate(user=admin)

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = client.post(
            '/api/v1/system-settings/upload-logo/',
            {
                'logo': SimpleUploadedFile(
                    'logo.svg', svg, content_type='image/svg+xml'
                )
            },
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        relative = SystemSettings.objects.get(key=SystemSettings.LOGO_FILE).value
        path = Path(tmp_path) / relative
        assert path.exists()
        assert path.read_bytes() == svg
        path.unlink(missing_ok=True)


@pytest.mark.django_db
@pytest.mark.parametrize('payload', [
    b'<svg xmlns="http://www.w3.org/2000/svg"><a href="https://evil.example/"><text>x</text></a></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div>html</div></foreignObject></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(https://evil.example/x)"/></svg>',
])
def test_active_or_external_svg_features_are_rejected(admin, tmp_path, payload):
    client = APIClient()
    client.force_authenticate(user=admin)

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = client.post(
            '/api/v1/system-settings/upload-logo/',
            {
                'logo': SimpleUploadedFile(
                    'logo.svg', payload, content_type='image/svg+xml'
                )
            },
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not SystemSettings.objects.filter(key=SystemSettings.LOGO_FILE).exists()
        system_dir = tmp_path / 'system'
        assert not system_dir.exists() or not any(system_dir.iterdir())
