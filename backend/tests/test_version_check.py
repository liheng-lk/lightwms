"""Tests for the automatic update/version check endpoint."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestVersionCheck:
    def test_version_endpoint_reports_newer_release_from_override(self, monkeypatch):
        cache.clear()
        monkeypatch.setenv('LIGHTWMS_VERSION', '1.1.4')
        monkeypatch.setenv('LIGHTWMS_LATEST_VERSION', '1.2.0')

        response = APIClient().get('/api/v1/version/')

        assert response.status_code == 200
        assert response.data['current_version'] == '1.1.4'
        assert response.data['latest_version'] == '1.2.0'
        assert response.data['update_available'] is True
        assert response.data['source'] == 'environment'
        assert response.data['error'] is None

    def test_version_endpoint_does_not_flag_same_or_older_release(self, monkeypatch):
        cache.clear()
        monkeypatch.setenv('LIGHTWMS_VERSION', '1.2.0')
        monkeypatch.setenv('LIGHTWMS_LATEST_VERSION', '1.1.9')

        response = APIClient().get('/api/v1/version/')

        assert response.status_code == 200
        assert response.data['update_available'] is False

    def test_version_endpoint_can_disable_remote_check(self, monkeypatch):
        cache.clear()
        monkeypatch.setenv('LIGHTWMS_VERSION', '1.2.0')
        monkeypatch.delenv('LIGHTWMS_LATEST_VERSION', raising=False)
        monkeypatch.setenv('UPDATE_CHECK_URL', '')

        response = APIClient().get('/api/v1/version/')

        assert response.status_code == 200
        assert response.data['latest_version'] is None
        assert response.data['update_available'] is False
        assert response.data['source'] == 'disabled'
