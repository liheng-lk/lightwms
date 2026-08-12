"""Concurrency regressions for one-time authentication resources."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import InviteCode, User, UserRole
from apps.users.services import AuthService, RegistrationService


@pytest.mark.django_db(transaction=True)
def test_same_refresh_can_only_be_consumed_once_concurrently():
    user = User.objects.create_user(
        username='refresh_race_user',
        password='StrongPass123!',
        role=UserRole.READ_ONLY_USER,
        is_active=True,
    )
    refresh = str(RefreshToken.for_user(user))
    barrier = Barrier(2)

    def consume():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            AuthService().refresh(refresh)
            return 'success'
        except InvalidToken:
            return 'invalid'
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume(), range(2)))

    assert sorted(results) == ['invalid', 'success']


@pytest.mark.django_db(transaction=True)
def test_single_use_invite_allows_only_one_concurrent_registration():
    admin = User.objects.create_user(
        username='invite_race_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    invite = InviteCode.objects.create(
        code='INV-RACE01',
        max_uses=1,
        current_uses=0,
        default_role=UserRole.READ_ONLY_USER,
        is_active=True,
        created_by=admin,
    )
    barrier = Barrier(2)

    def register(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            RegistrationService().simple_register(
                invite_code=invite.code,
                username=f'invite_race_user_{index}',
                password='StrongPass123!',
            )
            return 'success'
        except ValidationError:
            return 'invalid'
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(register, range(2)))

    invite.refresh_from_db()
    assert sorted(results) == ['invalid', 'success']
    assert invite.current_uses == 1
    assert User.objects.filter(username__startswith='invite_race_user_').count() == 1
