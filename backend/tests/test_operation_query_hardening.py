"""Strict input tests for borrow/take/replenish record queries."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='operation_query_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='operation_query_ordinary',
        password='StrongPass123!',
        role=UserRole.READ_ONLY_USER,
        is_active=True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize('path', [
    '/api/v1/borrow-records/',
    '/api/v1/take-records/',
    '/api/v1/replenish-records/',
])
def test_invalid_item_filter_returns_400(admin, path):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(path, {'item': 'not-an-int'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
@pytest.mark.parametrize('path', [
    '/api/v1/borrow-records/',
    '/api/v1/take-records/',
    '/api/v1/replenish-records/',
])
def test_invalid_date_is_not_silently_treated_as_unfiltered(admin, path):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(path, {'start_date': '2026-99-99'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
@pytest.mark.parametrize('path', [
    '/api/v1/borrow-records/',
    '/api/v1/take-records/',
    '/api/v1/replenish-records/',
])
def test_reversed_date_range_returns_400(admin, path):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(path, {
        'start_date': '2026-08-12',
        'end_date': '2026-08-11',
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
def test_invalid_borrow_status_returns_400(admin):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get('/api/v1/borrow-records/', {'status': 'overdue-ish'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
def test_ordinary_user_invalid_borrower_filter_is_still_rejected(ordinary):
    client = APIClient()
    client.force_authenticate(user=ordinary)

    response = client.get('/api/v1/borrow-records/', {'borrower': 'garbage'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
@pytest.mark.parametrize('path,field', [
    ('/api/v1/borrow-records/', 'borrower'),
    ('/api/v1/take-records/', 'taker'),
    ('/api/v1/replenish-records/', 'operator'),
])
def test_actor_id_above_bigint_range_returns_400(admin, path, field):
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(path, {field: 9_223_372_036_854_775_808})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 'VALIDATION_ERROR'
