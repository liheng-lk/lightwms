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


@pytest.fixture(autouse=True)
def assign_legacy_location_owner(request):
    """Adapt legacy API fixtures to the mandatory Location.owner contract.

    These modules predate location ownership and create Locations without an
    owner in setup code unrelated to the behavior under test. Production keeps
    the database field non-null; the compatibility shim supplies each module's
    existing manager fixture only while that legacy module constructs data.
    """
    owner_fixture_by_module = {
        'tests.test_borrow_api': 'item_manager',
        'tests.test_item_api': 'item_manager',
        'tests.test_search_api': 'item_manager',
        'tests.test_permissions_matrix': 'manager',
    }
    owner_fixture = owner_fixture_by_module.get(request.module.__name__)
    if owner_fixture is None:
        yield
        return

    manager = request.getfixturevalue(owner_fixture)
    from django.db.models.signals import pre_save
    from apps.inventory.models import Location

    dispatch_uid = 'tests.assign_legacy_location_owner'

    def ensure_owner(sender, instance, **kwargs):
        if instance.owner_id is None:
            instance.owner_id = manager.id

    pre_save.connect(
        ensure_owner,
        sender=Location,
        weak=False,
        dispatch_uid=dispatch_uid,
    )
    try:
        yield
    finally:
        pre_save.disconnect(sender=Location, dispatch_uid=dispatch_uid)
