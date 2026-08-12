"""Shared pytest compatibility fixtures for legacy module-level tests."""
from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.fixture(autouse=True)
def issue_legacy_wechat_state(request):
    """Give legacy invite-code tests a real one-time OAuth state row.

    The older test module used a hard-coded ``test_state`` before OAuth state
    validation became mandatory. Keep production validation strict while making
    those tests exercise the same database-backed state contract.
    """
    if request.module.__name__ != 'tests.test_invite_code':
        yield
        return

    request.getfixturevalue('db')
    from apps.users.models import WechatOAuthState

    WechatOAuthState.objects.update_or_create(
        state='test_state',
        defaults={
            'redirect_uri': 'http://localhost:8000/api/v1/auth/wechat/callback/',
            'expires_at': timezone.now() + timedelta(minutes=10),
        },
    )
    yield
