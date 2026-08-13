"""Input validation tests for inventory list filters."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='inventory_filter_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
class TestInventoryListFilterContract:
    @pytest.mark.parametrize('field,value', [
        ('category', 'not-an-int'),
        ('location', '1.5'),
        ('warehouse', 'NaN'),
        ('owner', '-1'),
    ])
    def test_invalid_integer_filters_return_400(self, admin, field, value):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/items/', {field: value})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    @pytest.mark.parametrize('field,value', [
        ('type', 'invalid-type'),
        ('status', 'invalid-status'),
    ])
    def test_invalid_choice_filters_return_400(self, admin, field, value):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/items/', {field: value})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'
