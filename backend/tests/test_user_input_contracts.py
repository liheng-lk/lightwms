"""Regression tests for user input contracts discovered during repository audit."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole
from apps.users.serializers import (
    RegisterSerializer,
    SimpleRegisterSerializer,
    UserCreateSerializer,
)


@pytest.mark.parametrize(
    ('serializer_class', 'payload'),
    [
        (
            RegisterSerializer,
            {
                'wechat_session_id': 'session-123',
                'invite_code': 'INV-123',
                'username': 'abc_!@#',
                'password': 'StrongPass123!',
            },
        ),
        (
            SimpleRegisterSerializer,
            {
                'invite_code': 'INV-123',
                'username': 'abc_!@#',
                'password': 'StrongPass123!',
            },
        ),
        (
            UserCreateSerializer,
            {
                'username': 'abc_!@#',
                'password': 'StrongPass123!',
                'role': UserRole.READ_ONLY_USER,
            },
        ),
    ],
)
def test_every_account_creation_serializer_rejects_illegal_username(serializer_class, payload):
    serializer = serializer_class(data=payload)

    assert not serializer.is_valid()
    assert 'username' in serializer.errors


@pytest.mark.parametrize('username', ['abc_123', 'User2026', '测试用户_01'])
@pytest.mark.parametrize(
    ('serializer_class', 'base_payload'),
    [
        (
            RegisterSerializer,
            {
                'wechat_session_id': 'session-123',
                'invite_code': 'INV-123',
                'password': 'StrongPass123!',
            },
        ),
        (
            SimpleRegisterSerializer,
            {
                'invite_code': 'INV-123',
                'password': 'StrongPass123!',
            },
        ),
        (
            UserCreateSerializer,
            {
                'password': 'StrongPass123!',
                'role': UserRole.READ_ONLY_USER,
            },
        ),
    ],
)
def test_every_account_creation_serializer_accepts_same_legal_usernames(
    username, serializer_class, base_payload
):
    serializer = serializer_class(data={**base_payload, 'username': username})

    assert serializer.is_valid(), serializer.errors


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='query_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
    )


@pytest.fixture
def authenticated_admin(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


@pytest.mark.django_db
class TestUserListQueryContract:
    def test_username_search_is_applied_by_backend(self, authenticated_admin):
        needle = User.objects.create_user(
            username='needle_account',
            password='StrongPass123!',
            role=UserRole.READ_ONLY_USER,
        )
        User.objects.create_user(
            username='unrelated_account',
            password='StrongPass123!',
            role=UserRole.READ_ONLY_USER,
        )

        response = authenticated_admin.get('/api/v1/users/?search=needle')

        assert response.status_code == status.HTTP_200_OK
        usernames = [row['username'] for row in response.data['results']]
        assert usernames == [needle.username]

    @pytest.mark.parametrize(
        'query',
        [
            'role=not-a-role',
            'is_active=definitely-not-a-boolean',
            'date_from=not-a-date',
            'date_to=2026-99-99',
            f"search={'x' * 101}",
        ],
    )
    def test_invalid_filters_return_400_instead_of_being_silently_ignored(
        self, authenticated_admin, query
    ):
        response = authenticated_admin.get(f'/api/v1/users/?{query}')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_reversed_date_range_returns_400(self, authenticated_admin):
        response = authenticated_admin.get(
            '/api/v1/users/?date_from=2026-08-20&date_to=2026-08-19'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'
        assert 'date_to' in response.data['details']

    def test_valid_role_status_and_date_filters_remain_supported(self, authenticated_admin):
        response = authenticated_admin.get(
            '/api/v1/users/?role=super_admin&is_active=true&date_from=2020-01-01'
        )

        assert response.status_code == status.HTTP_200_OK
        assert all(row['role'] == UserRole.SUPER_ADMIN for row in response.data['results'])
        assert all(row['is_active'] is True for row in response.data['results'])

    def test_non_super_admin_still_cannot_list_users(self, db):
        user = User.objects.create_user(
            username='query_regular',
            password='StrongPass123!',
            role=UserRole.READ_ONLY_USER,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/users/?search=query')

        assert response.status_code == status.HTTP_403_FORBIDDEN
