"""Database integer boundary tests for list/search query parameters."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='query_bigint_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize('path', ['/api/v1/search/', '/api/v1/items/'])
def test_filter_id_above_postgres_bigint_returns_400(admin, path):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(path, {'owner': 9_223_372_036_854_775_808})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'
