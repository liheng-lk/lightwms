"""Tests for non-blocking application update detection."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.settings import version_views
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='version_admin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
class TestVersionCheck:
    def test_detects_newer_published_version(self, admin, monkeypatch):
        cache.delete(version_views._CACHE_KEY)
        monkeypatch.setenv('APP_VERSION', '1.1.4')
        monkeypatch.setattr(version_views, '_latest_dockerhub_version', lambda: '1.2.0')
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/system-settings/version/?force=true')

        assert response.status_code == 200
        assert response.data['current_version'] == '1.1.4'
        assert response.data['latest_version'] == '1.2.0'
        assert response.data['update_available'] is True
        assert response.data['check_ok'] is True

    def test_network_failure_does_not_break_endpoint(self, admin, monkeypatch):
        cache.delete(version_views._CACHE_KEY)
        monkeypatch.setenv('APP_VERSION', '1.1.4')

        def fail():
            raise OSError('offline')

        monkeypatch.setattr(version_views, '_latest_dockerhub_version', fail)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/system-settings/version/?force=true')

        assert response.status_code == 200
        assert response.data['current_version'] == '1.1.4'
        assert response.data['latest_version'] is None
        assert response.data['update_available'] is False
        assert response.data['check_ok'] is False
