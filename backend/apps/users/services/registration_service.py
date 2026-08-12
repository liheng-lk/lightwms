"""
Registration service for LightWMS.
Handles WeChat OAuth flow and user registration with invite codes.
"""
import hashlib
import secrets
from datetime import timedelta
from typing import Optional, NamedTuple
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.users.models import User, InviteCode, WechatOAuthState, WechatSession
from apps.users.services.invite_code_service import InviteCodeService


class WechatOAuthResult(NamedTuple):
    session_id: str
    openid: str
    nickname: str


class RegistrationService:
    """Service for user registration via WeChat OAuth and invite codes."""

    SESSION_EXPIRY_MINUTES = 10
    OAUTH_STATE_EXPIRY_MINUTES = 10
    MOCK_WECHAT_OAUTH_URL = 'https://open.weixin.qq.com/connect/oauth2/authorize'

    def __init__(self):
        self.invite_code_service = InviteCodeService()

    def _allowed_redirect_uris(self):
        configured = getattr(settings, 'WECHAT_REDIRECT_URI', '')
        allowed = getattr(settings, 'WECHAT_ALLOWED_REDIRECT_URIS', None)
        if allowed is None:
            allowed = [configured] if configured else []
        return {str(uri).strip() for uri in allowed if str(uri).strip()}

    def _validate_redirect_uri(self, redirect_uri: Optional[str]) -> str:
        configured = getattr(
            settings,
            'WECHAT_REDIRECT_URI',
            'http://localhost:8000/api/v1/auth/wechat/callback/'
        )
        callback_uri = redirect_uri or configured
        try:
            parsed = urlsplit(callback_uri)
        except ValueError as exc:
            raise ValidationError({'redirect_uri': 'Invalid redirect URI.'}) from exc
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValidationError({'redirect_uri': 'Invalid redirect URI.'})

        allowed = self._allowed_redirect_uris()
        if allowed and callback_uri not in allowed:
            raise ValidationError({'redirect_uri': 'Redirect URI is not allowed.'})
        return callback_uri

    def initiate_wechat_oauth(self, redirect_uri: Optional[str] = None) -> str:
        app_id = getattr(settings, 'WECHAT_APP_ID', 'mock_app_id')
        callback_uri = self._validate_redirect_uri(redirect_uri)
        state = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(minutes=self.OAUTH_STATE_EXPIRY_MINUTES)

        # Opportunistic cleanup keeps the one-time state table bounded without
        # requiring a background scheduler for correctness.
        WechatOAuthState.objects.filter(expires_at__lt=timezone.now()).delete()
        WechatOAuthState.objects.create(
            state=state,
            redirect_uri=callback_uri,
            expires_at=expires_at,
        )

        query = urlencode({
            'appid': app_id,
            'redirect_uri': callback_uri,
            'response_type': 'code',
            'scope': 'snsapi_userinfo',
            'state': state,
        })
        return f'{self.MOCK_WECHAT_OAUTH_URL}?{query}#wechat_redirect'

    @transaction.atomic
    def handle_wechat_callback(
        self,
        code: str,
        state: Optional[str] = None
    ) -> WechatOAuthResult:
        if not state:
            raise ValidationError({'state': 'OAuth state is required.'})

        # A state row is consumed in the same transaction as creation of the
        # temporary registration session. select_for_update makes duplicate
        # callbacks serialize; the second request sees no state row.
        try:
            oauth_state = WechatOAuthState.objects.select_for_update().get(state=state)
        except WechatOAuthState.DoesNotExist:
            raise ValidationError({'state': 'Invalid or already used OAuth state.'})

        if oauth_state.is_expired:
            oauth_state.delete()
            raise ValidationError({'state': 'OAuth state has expired.'})

        if not code:
            raise ValidationError({'code': 'OAuth code is required.'})

        # The local implementation is a mock of the provider exchange. A
        # deterministic identity for the same code makes replay/duplicate
        # identity behavior testable instead of creating a fresh fake identity
        # every time.
        mock_openid = f"mock_openid_{hashlib.sha256(code.encode()).hexdigest()[:24]}"
        mock_nickname = f"User_{code[:6]}"
        session_id = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(minutes=self.SESSION_EXPIRY_MINUTES)

        oauth_state.delete()
        WechatSession.objects.create(
            session_id=session_id,
            openid=mock_openid,
            nickname=mock_nickname,
            expires_at=expires_at
        )

        return WechatOAuthResult(
            session_id=session_id,
            openid=mock_openid,
            nickname=mock_nickname
        )

    def register(
        self,
        wechat_session_id: str,
        invite_code: str,
        username: str,
        password: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        department: Optional[str] = None
    ) -> User:
        """Register a user after atomically consuming session and invite code."""
        with transaction.atomic():
            try:
                session = WechatSession.objects.select_for_update().get(
                    session_id=wechat_session_id
                )
            except WechatSession.DoesNotExist:
                raise ValidationError({
                    'wechat_session_id': 'Invalid or expired session.'
                })

            if session.is_expired:
                session.delete()
                raise ValidationError({
                    'wechat_session_id': 'Session has expired. Please restart the registration process.'
                })

            if User.objects.filter(wechat_openid=session.openid).exists():
                raise ValidationError({
                    'wechat_openid': 'This WeChat account is already registered.'
                })

            validated_invite_code = self.invite_code_service.validate_and_use(invite_code)
            self._validate_identity(username=username, phone=phone)

            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    phone=phone or None,
                    email=email or None,
                    department=department or '',
                    wechat_openid=session.openid,
                    role=validated_invite_code.default_role,
                    is_active=True
                )
            except IntegrityError as exc:
                # Preserve transaction atomicity while exposing a stable API
                # error for a concurrent username/phone/WeChat identity race.
                raise ValidationError({
                    'registration': 'Account identity is already registered.'
                }) from exc

            self._log_invite_use(invite_code=validated_invite_code, user=user)
            session.delete()
            return user

    def simple_register(
        self,
        invite_code: str,
        username: str,
        password: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        department: Optional[str] = None
    ) -> User:
        with transaction.atomic():
            validated_invite_code = self.invite_code_service.validate_and_use(invite_code)
            self._validate_identity(username=username, phone=phone)

            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    phone=phone or None,
                    email=email or None,
                    department=department or '',
                    role=validated_invite_code.default_role,
                    is_active=True
                )
            except IntegrityError as exc:
                raise ValidationError({
                    'registration': 'Account identity is already registered.'
                }) from exc

            self._log_invite_use(invite_code=validated_invite_code, user=user)
            return user

    def _validate_identity(self, username: str, phone: Optional[str] = None) -> None:
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'This username is already taken.'})
        if phone and User.objects.filter(phone=phone).exists():
            raise ValidationError({'phone': 'This phone number is already registered.'})

    def _log_invite_use(self, invite_code: InviteCode, user: User) -> None:
        """Record a minimal invite-use audit without storing the invite secret."""
        from apps.audit.models import AuditAction, AuditLog, TargetType
        AuditLog.objects.create(
            action=AuditAction.INVITE_USE,
            target_type=TargetType.USER,
            target_id=user.id,
            diff={
                'before': None,
                'after': {
                    'user_id': user.id,
                    'role': user.role,
                    'invite_code_id': invite_code.id,
                },
            },
            operator=None,
            operator_role='registration',
        )

    def cleanup_expired_sessions(self) -> int:
        expired_sessions = WechatSession.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        WechatOAuthState.objects.filter(expires_at__lt=timezone.now()).delete()
        return count
