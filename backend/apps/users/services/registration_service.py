"""
Registration service for LightWMS.
Handles WeChat OAuth flow and user registration with invite codes.
"""
import secrets
from datetime import timedelta
from typing import Optional, NamedTuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.users.models import User, InviteCode, WechatSession
from apps.users.services.invite_code_service import InviteCodeService


class WechatOAuthResult(NamedTuple):
    """Result of WeChat OAuth callback."""
    session_id: str
    openid: str
    nickname: str


class RegistrationService:
    """Service for user registration via WeChat OAuth and invite codes."""

    SESSION_EXPIRY_MINUTES = 10
    MOCK_WECHAT_OAUTH_URL = 'https://open.weixin.qq.com/connect/oauth2/authorize'

    def __init__(self):
        self.invite_code_service = InviteCodeService()

    def initiate_wechat_oauth(self, redirect_uri: Optional[str] = None) -> str:
        app_id = getattr(settings, 'WECHAT_APP_ID', 'mock_app_id')
        callback_uri = redirect_uri or getattr(
            settings,
            'WECHAT_REDIRECT_URI',
            'http://localhost:8000/api/v1/auth/wechat/callback/'
        )
        state = secrets.token_urlsafe(16)
        return (
            f"{self.MOCK_WECHAT_OAUTH_URL}"
            f"?appid={app_id}"
            f"&redirect_uri={callback_uri}"
            f"&response_type=code"
            f"&scope=snsapi_userinfo"
            f"&state={state}"
            f"#wechat_redirect"
        )

    def handle_wechat_callback(
        self,
        code: str,
        state: Optional[str] = None
    ) -> WechatOAuthResult:
        mock_openid = f"mock_openid_{secrets.token_hex(8)}"
        mock_nickname = f"User_{code[:6]}" if code else "MockUser"
        session_id = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(minutes=self.SESSION_EXPIRY_MINUTES)

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
        """Register a user after validating both WeChat session and invite code."""
        with transaction.atomic():
            try:
                session = WechatSession.objects.get(session_id=wechat_session_id)
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

            user = User.objects.create_user(
                username=username,
                password=password,
                phone=phone,
                email=email,
                department=department or '',
                wechat_openid=session.openid,
                role=validated_invite_code.default_role,
                is_active=True
            )

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
        """
        Register a user with a database-backed invite code.

        There are deliberately no hard-coded or permanent invite-code bypasses:
        every registration must consume a valid, active, non-expired code so
        administrators can revoke access and audit registrations consistently.
        """
        with transaction.atomic():
            validated_invite_code = self.invite_code_service.validate_and_use(invite_code)
            self._validate_identity(username=username, phone=phone)

            user = User.objects.create_user(
                username=username,
                password=password,
                phone=phone,
                email=email,
                department=department or '',
                role=validated_invite_code.default_role,
                is_active=True
            )

            self._log_invite_use(invite_code=validated_invite_code, user=user)
            return user

    def _validate_identity(self, username: str, phone: Optional[str] = None) -> None:
        if User.objects.filter(username=username).exists():
            raise ValidationError({
                'username': 'This username is already taken.'
            })
        if phone and User.objects.filter(phone=phone).exists():
            raise ValidationError({
                'phone': 'This phone number is already registered.'
            })

    def _log_invite_use(self, invite_code: InviteCode, user: User) -> None:
        """Hook for invite-use auditing; never log invite secrets or passwords."""
        try:
            from apps.audit.models import AuditLog
            # Kept as a compatibility hook until invite-code audit action types
            # are formalized. Registration itself remains transactional.
            _ = AuditLog
        except ImportError:
            pass

    def cleanup_expired_sessions(self) -> int:
        expired_sessions = WechatSession.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        return count
