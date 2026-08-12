"""Attack-style tests for authentication, registration and invite-code flows."""
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import LoginLog
from apps.users.models import InviteCode, User, UserRole, WechatSession
from core.middleware import RequestContextMiddleware


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='auth_hard_admin', password='StrongPass123!',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username='auth_hard_user_a', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username='auth_hard_user_b', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def invite(admin):
    return InviteCode.objects.create(
        code='INV-AUTH01', max_uses=2, current_uses=0,
        default_role=UserRole.READ_ONLY_USER,
        is_active=True, created_by=admin,
    )


def login(client, user, password='StrongPass123!'):
    response = client.post('/api/v1/auth/login/', {
        'username': user.username,
        'password': password,
    }, format='json')
    assert response.status_code == status.HTTP_200_OK
    return response.data


@pytest.mark.django_db
class TestRefreshAndLogoutOwnership:
    def test_rotated_refresh_cannot_be_reused(self, user_a):
        client = APIClient()
        tokens = login(client, user_a)

        first = client.post('/api/v1/auth/refresh/', {'refresh': tokens['refresh']}, format='json')
        second = client.post('/api/v1/auth/refresh/', {'refresh': tokens['refresh']}, format='json')

        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_cannot_logout_another_users_refresh(self, user_a, user_b):
        client_a = APIClient()
        client_b = APIClient()
        tokens_a = login(client_a, user_a)
        tokens_b = login(client_b, user_b)
        client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_a['access']}")

        response = client_a.post(
            '/api/v1/auth/logout/',
            {'refresh': tokens_b['refresh']},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Victim's refresh remains usable.
        still_valid = APIClient().post(
            '/api/v1/auth/refresh/',
            {'refresh': tokens_b['refresh']},
            format='json',
        )
        assert still_valid.status_code == status.HTTP_200_OK

    def test_disabled_user_refresh_is_rejected_and_token_blacklisted(self, user_a):
        client = APIClient()
        tokens = login(client, user_a)
        user_a.is_active = False
        user_a.save(update_fields=['is_active'])

        response = client.post('/api/v1/auth/refresh/', {'refresh': tokens['refresh']}, format='json')
        replay = client.post('/api/v1/auth/refresh/', {'refresh': tokens['refresh']}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert replay.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWechatOAuthState:
    def _authorize(self, query=''):
        response = APIClient().get(f'/api/v1/auth/wechat/authorize/{query}')
        assert response.status_code == status.HTTP_200_OK
        parsed = urlparse(response.data['authorize_url'])
        state = parse_qs(parsed.query)['state'][0]
        assert state
        return state

    def test_callback_requires_exact_state_issued_by_authorize(self):
        state = self._authorize()
        client = APIClient()

        missing = client.post('/api/v1/auth/wechat/callback/', {'code': 'abc123'}, format='json')
        wrong = client.post(
            '/api/v1/auth/wechat/callback/',
            {'code': 'abc123', 'state': 'attacker-state'},
            format='json',
        )
        correct = client.post(
            '/api/v1/auth/wechat/callback/',
            {'code': 'abc123', 'state': state},
            format='json',
        )

        assert missing.status_code == status.HTTP_400_BAD_REQUEST
        assert wrong.status_code == status.HTTP_400_BAD_REQUEST
        assert correct.status_code == status.HTTP_200_OK

    def test_oauth_state_is_single_use(self):
        state = self._authorize()
        client = APIClient()

        first = client.post(
            '/api/v1/auth/wechat/callback/',
            {'code': 'one-time-code', 'state': state},
            format='json',
        )
        replay = client.post(
            '/api/v1/auth/wechat/callback/',
            {'code': 'one-time-code', 'state': state},
            format='json',
        )

        assert first.status_code == status.HTTP_200_OK
        assert replay.status_code == status.HTTP_400_BAD_REQUEST
        assert WechatSession.objects.count() == 1

    def test_expired_oauth_state_is_rejected(self):
        state = self._authorize()
        from apps.users.models import WechatOAuthState
        WechatOAuthState.objects.filter(state=state).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = APIClient().post(
            '/api/v1/auth/wechat/callback/',
            {'code': 'expired-state-code', 'state': state},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not WechatSession.objects.exists()

    @override_settings(
        WECHAT_REDIRECT_URI='https://wms.example.com/api/v1/auth/wechat/callback/',
        WECHAT_ALLOWED_REDIRECT_URIS=[
            'https://wms.example.com/api/v1/auth/wechat/callback/',
        ],
    )
    def test_authorize_rejects_unapproved_redirect_uri(self):
        response = APIClient().get(
            '/api/v1/auth/wechat/authorize/?redirect_uri=https%3A%2F%2Fevil.example%2Fsteal'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @override_settings(
        WECHAT_REDIRECT_URI='https://wms.example.com/api/v1/auth/wechat/callback/',
        WECHAT_ALLOWED_REDIRECT_URIS=[
            'https://wms.example.com/api/v1/auth/wechat/callback/',
        ],
    )
    def test_authorize_accepts_exact_allowlisted_redirect_uri(self):
        response = APIClient().get(
            '/api/v1/auth/wechat/authorize/?redirect_uri='
            'https%3A%2F%2Fwms.example.com%2Fapi%2Fv1%2Fauth%2Fwechat%2Fcallback%2F'
        )

        assert response.status_code == status.HTTP_200_OK
        redirect_uri = parse_qs(urlparse(response.data['authorize_url']).query)['redirect_uri'][0]
        assert redirect_uri == 'https://wms.example.com/api/v1/auth/wechat/callback/'


@pytest.mark.django_db
class TestRegistrationAtomicity:
    def test_wechat_session_is_single_use(self, invite):
        session = WechatSession.objects.create(
            session_id='single-use-session',
            openid='single-use-openid',
            nickname='Single Use',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        client = APIClient()
        payload = {
            'wechat_session_id': session.session_id,
            'invite_code': invite.code,
            'username': 'wechat_once_user',
            'password': 'StrongPass123!',
        }

        first = client.post('/api/v1/auth/register/wechat/', payload, format='json')
        payload['username'] = 'wechat_replay_user'
        second = client.post('/api/v1/auth/register/wechat/', payload, format='json')

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        invite.refresh_from_db()
        assert invite.current_uses == 1
        assert User.objects.filter(wechat_openid='single-use-openid').count() == 1

    def test_duplicate_username_rolls_back_invite_consumption(self, invite, user_a):
        client = APIClient()

        response = client.post('/api/v1/auth/register/', {
            'invite_code': invite.code,
            'username': user_a.username,
            'password': 'StrongPass123!',
        }, format='json')

        # Duplicate account identity is a conflict, but the registration
        # transaction must still roll back the invite usage increment.
        assert response.status_code == status.HTTP_409_CONFLICT
        invite.refresh_from_db()
        assert invite.current_uses == 0

    def test_expired_wechat_session_does_not_consume_invite(self, invite):
        session = WechatSession.objects.create(
            session_id='expired-register-session',
            openid='expired-register-openid',
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        client = APIClient()

        response = client.post('/api/v1/auth/register/wechat/', {
            'wechat_session_id': session.session_id,
            'invite_code': invite.code,
            'username': 'expired_session_user',
            'password': 'StrongPass123!',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        invite.refresh_from_db()
        assert invite.current_uses == 0


@pytest.mark.django_db
class TestInviteCodeUpdateBounds:
    def test_admin_cannot_lower_max_uses_below_current_uses(self, admin):
        invite = InviteCode.objects.create(
            code='INV-USED01',
            max_uses=5,
            current_uses=3,
            default_role=UserRole.READ_ONLY_USER,
            is_active=True,
            created_by=admin,
        )
        client = APIClient()
        tokens = login(client, admin)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = client.patch(
            f'/api/v1/invite-codes/{invite.id}/',
            {'max_uses': 2},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        invite.refresh_from_db()
        assert invite.max_uses == 5
        assert invite.current_uses == 3

    def test_admin_may_set_max_uses_equal_to_current_uses(self, admin):
        invite = InviteCode.objects.create(
            code='INV-USED02',
            max_uses=5,
            current_uses=3,
            default_role=UserRole.READ_ONLY_USER,
            is_active=True,
            created_by=admin,
        )
        client = APIClient()
        tokens = login(client, admin)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = client.patch(
            f'/api/v1/invite-codes/{invite.id}/',
            {'max_uses': 3},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        invite.refresh_from_db()
        assert invite.max_uses == 3
        assert invite.status == 'exhausted'


class TestClientIPTrustBoundary:
    def _request(self, remote_addr, xff=None, real_ip=None):
        factory = RequestFactory()
        extra = {'REMOTE_ADDR': remote_addr}
        if xff is not None:
            extra['HTTP_X_FORWARDED_FOR'] = xff
        if real_ip is not None:
            extra['HTTP_X_REAL_IP'] = real_ip
        return factory.get('/api/v1/auth/login/', **extra)

    @override_settings(TRUSTED_PROXY_CIDRS=[])
    def test_untrusted_peer_cannot_spoof_forwarded_headers(self):
        middleware = RequestContextMiddleware(lambda request: None)
        request = self._request(
            '203.0.113.10',
            xff='198.51.100.7',
            real_ip='198.51.100.8',
        )

        assert middleware.get_client_ip(request) == '203.0.113.10'

    @override_settings(TRUSTED_PROXY_CIDRS=['172.16.0.0/12'])
    def test_trusted_proxy_uses_proxy_overwritten_real_ip(self):
        middleware = RequestContextMiddleware(lambda request: None)
        request = self._request(
            '172.18.0.4',
            xff='198.51.100.99, 203.0.113.11',
            real_ip='203.0.113.11',
        )

        # X-Real-IP is overwritten by the shipped Nginx config and therefore
        # is not vulnerable to a client-prepended X-Forwarded-For value.
        assert middleware.get_client_ip(request) == '203.0.113.11'


@pytest.mark.django_db
class TestLoginIPEndToEnd:
    @override_settings(TRUSTED_PROXY_CIDRS=[])
    def test_untrusted_forwarded_headers_do_not_pollute_login_log(self, user_a):
        client = APIClient()

        response = client.post(
            '/api/v1/auth/login/',
            {'username': user_a.username, 'password': 'wrong-password'},
            format='json',
            REMOTE_ADDR='203.0.113.10',
            HTTP_X_FORWARDED_FOR='198.51.100.7',
            HTTP_X_REAL_IP='198.51.100.8',
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        log = LoginLog.objects.filter(username_attempted=user_a.username).latest('created_at')
        assert log.ip == '203.0.113.10'
