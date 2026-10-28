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


@pytest.fixture
def reader(db):
    return User.objects.create_user(
        username='version_reader',
        password='testpass123',
        role=UserRole.READ_ONLY_USER,
        is_active=True,
    )


def _fake_tags(rows_by_repo):
    def fetch(repo):
        return rows_by_repo.get(repo, [])
    return fetch


def _get(user, force=True):
    client = APIClient()
    client.force_authenticate(user=user)
    suffix = '?force=true' if force else ''
    return client.get(f'/api/v1/system-settings/version/{suffix}')


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    cache.delete(version_views._CACHE_KEY)
    for name in ('APP_VERSION', 'BUILD_TIME', 'IMAGE_TAG', 'APP_REVISION'):
        monkeypatch.delenv(name, raising=False)
    yield
    cache.delete(version_views._CACHE_KEY)


@pytest.mark.django_db
class TestVersionCheck:
    def test_detects_newer_published_version(self, admin, monkeypatch):
        monkeypatch.setenv('APP_VERSION', '1.1.4')
        monkeypatch.setattr(version_views, '_fetch_tags', _fake_tags({
            'lightwms-backend': [{'name': '1.2.0'}, {'name': 'latest'}],
        }))

        response = _get(admin)

        assert response.status_code == 200
        assert response.data['current_version'] == '1.1.4'
        assert response.data['latest_version'] == '1.2.0'
        assert response.data['update_available'] is True
        assert response.data['update_reason'] == 'new_version'
        assert response.data['check_ok'] is True

    def test_frontend_only_release_is_detected(self, admin, monkeypatch):
        monkeypatch.setenv('APP_VERSION', '1.2.0')
        monkeypatch.setattr(version_views, '_fetch_tags', _fake_tags({
            'lightwms-backend': [{'name': '1.2.0'}],
            'lightwms-frontend': [{'name': '1.2.1'}],
        }))

        assert _get(admin).data['latest_version'] == '1.2.1'

    def test_detects_republished_tag_without_version_bump(self, admin, monkeypatch):
        monkeypatch.setenv('APP_VERSION', '1.2.1')
        monkeypatch.setenv('BUILD_TIME', '2026-10-01T08:00:00Z')
        monkeypatch.setenv('IMAGE_TAG', 'latest')
        monkeypatch.setattr(version_views, '_fetch_tags', _fake_tags({
            'lightwms-backend': [
                {'name': '1.2.1', 'last_updated': '2026-10-20T08:00:00Z'},
                {'name': 'latest', 'last_updated': '2026-10-20T08:00:00Z'},
            ],
        }))

        data = _get(admin).data

        assert data['update_available'] is True
        assert data['update_reason'] == 'image_republished'

    def test_own_release_push_is_not_reported(self, admin, monkeypatch):
        # Pushed a few minutes after this very image was built.
        monkeypatch.setenv('APP_VERSION', '1.2.1')
        monkeypatch.setenv('BUILD_TIME', '2026-10-01T08:00:00Z')
        monkeypatch.setenv('IMAGE_TAG', 'latest')
        monkeypatch.setattr(version_views, '_fetch_tags', _fake_tags({
            'lightwms-backend': [
                {'name': '1.2.1', 'last_updated': '2026-10-01T08:06:00Z'},
                {'name': 'latest', 'last_updated': '2026-10-01T08:06:00Z'},
            ],
        }))

        assert _get(admin).data['update_available'] is False

    def test_network_failure_does_not_break_endpoint(self, admin, monkeypatch):
        monkeypatch.setenv('APP_VERSION', '1.1.4')

        def fail(repo):
            raise OSError('offline')

        monkeypatch.setattr(version_views, '_fetch_tags', fail)

        response = _get(admin)

        assert response.status_code == 200
        assert response.data['current_version'] == '1.1.4'
        assert response.data['latest_version'] is None
        assert response.data['update_available'] is False
        assert response.data['check_ok'] is False

    def test_force_refresh_requires_super_admin(self, reader, monkeypatch):
        monkeypatch.setattr(version_views, '_fetch_tags', _fake_tags({}))
        assert _get(reader, force=True).status_code == 403
        assert _get(reader, force=False).status_code == 200
