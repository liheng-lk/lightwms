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

from apps.users.models import User, UserRole, InviteCode, WechatSession
from apps.users.services.invite_code_service import InviteCodeService


class WechatOAuthResult(NamedTuple):
    """Result of WeChat OAuth callback."""
    session_id: str
    openid: str
    nickname: str


class RegistrationService:
    """
    Service for user registration via WeChat OAuth and invite codes.
    
    The registration flow:
    1. User initiates WeChat OAuth (initiate_wechat_oauth)
    2. WeChat redirects back with code (handle_wechat_callback)
    3. User submits registration form with invite code (register)
    
    Note: WeChat OAuth is currently mocked for development.
    """
    
    # Session expiration time (10 minutes)
    SESSION_EXPIRY_MINUTES = 10
    
    # Mock WeChat OAuth URL (replace with real URL in production)
    MOCK_WECHAT_OAUTH_URL = 'https://open.weixin.qq.com/connect/oauth2/authorize'
    
    def __init__(self):
        self.invite_code_service = InviteCodeService()
    
    def initiate_wechat_oauth(self, redirect_uri: Optional[str] = None) -> str:
        """
        Initiate WeChat OAuth flow.
        
        In production, this would redirect to WeChat's authorization URL.
        Currently returns a mock URL for development.
        
        Args:
            redirect_uri: Optional callback URL override
        
        Returns:
            WeChat authorization URL
        """
        # Get app ID from settings (mock value for development)
        app_id = getattr(settings, 'WECHAT_APP_ID', 'mock_app_id')
        
        # Use provided redirect_uri or default from settings
        callback_uri = redirect_uri or getattr(
            settings, 
            'WECHAT_REDIRECT_URI', 
            'http://localhost:8000/api/v1/auth/wechat/callback/'
        )
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(16)
        
        # Build OAuth URL (mock for development)
        oauth_url = (
            f"{self.MOCK_WECHAT_OAUTH_URL}"
            f"?appid={app_id}"
            f"&redirect_uri={callback_uri}"
            f"&response_type=code"
            f"&scope=snsapi_userinfo"
            f"&state={state}"
            f"#wechat_redirect"
        )
        
        return oauth_url
    
    def handle_wechat_callback(
        self, 
        code: str, 
        state: Optional[str] = None
    ) -> WechatOAuthResult:
        """
        Handle WeChat OAuth callback.
        
        In production, this would:
        1. Exchange code for access_token
        2. Use access_token to get user info (openid, nickname, etc.)
        
        Currently returns mock data for development.
        
        Args:
            code: Authorization code from WeChat
            state: State parameter for CSRF verification
        
        Returns:
            WechatOAuthResult with session_id and user info
        """
        # In production, exchange code for access_token and get user info
        # For now, generate mock openid based on code
        mock_openid = f"mock_openid_{secrets.token_hex(8)}"
        mock_nickname = f"User_{code[:6]}" if code else "MockUser"
        
        # Create a temporary session to store the openid
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
        """
        Register a new user with WeChat session and invite code.
        
        This method:
        1. Validates the WeChat session
        2. Validates and uses the invite code (atomic)
        3. Creates the user with the invite code's default role
        4. Creates an audit log entry
        
        Args:
            wechat_session_id: Session ID from WeChat OAuth callback
            invite_code: Invite code for registration
            username: Desired username
            password: User password
            phone: Optional phone number
            email: Optional email address
            department: Optional department name
        
        Returns:
            Created User instance
        
        Raises:
            ValidationError: If session is invalid/expired, invite code is invalid,
                           or username/phone already exists
        """
        with transaction.atomic():
            # Validate WeChat session
            try:
                session = WechatSession.objects.get(session_id=wechat_session_id)
            except WechatSession.DoesNotExist:
                raise ValidationError({
                    'wechat_session_id': 'Invalid or expired session.'
                })
            
            if session.is_expired:
                # Clean up expired session
                session.delete()
                raise ValidationError({
                    'wechat_session_id': 'Session has expired. Please restart the registration process.'
                })
            
            # Check if openid is already registered
            if User.objects.filter(wechat_openid=session.openid).exists():
                raise ValidationError({
                    'wechat_openid': 'This WeChat account is already registered.'
                })
            
            # Validate and use invite code (this also locks the row)
            validated_invite_code = self.invite_code_service.validate_and_use(invite_code)
            
            # Validate username uniqueness
            if User.objects.filter(username=username).exists():
                raise ValidationError({
                    'username': 'This username is already taken.'
                })
            
            # Validate phone uniqueness if provided
            if phone and User.objects.filter(phone=phone).exists():
                raise ValidationError({
                    'phone': 'This phone number is already registered.'
                })
            
            # Create user with role from invite code
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
            
            # Create audit log for invite code usage
            self._log_invite_use(
                invite_code=validated_invite_code,
                user=user
            )
            
            # Clean up the WeChat session
            session.delete()
            
            return user
    
    def _log_invite_use(self, invite_code: InviteCode, user: User) -> None:
        """
        Create audit log entry for invite code usage.
        
        Args:
            invite_code: The invite code that was used
            user: The user who registered with the code
        """
        # Import here to avoid circular imports
        # AuditLog will be implemented in Task 17
        # For now, we'll just pass - the audit log creation will be added later
        try:
            from apps.audit.models import AuditLog
            # AuditLog creation will be implemented in Task 17
            # For now, this is a placeholder
            pass
        except ImportError:
            # AuditLog not yet implemented
            pass
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired WeChat sessions.
        
        This should be called periodically (e.g., via celery task or cron).
        
        Returns:
            Number of sessions deleted
        """
        expired_sessions = WechatSession.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        return count
    
    # Hardcoded permanent invite code (bypasses database validation)
    # Note: Comparison is case-insensitive
    BUILTIN_INVITE_CODE = 'hdu340'
    BUILTIN_INVITE_CODE_ROLE = UserRole.ITEM_MANAGER
    
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
        Register a new user with invite code only (no WeChat OAuth required).
        
        This method:
        1. Validates and uses the invite code (atomic)
        2. Creates the user with the invite code's default role
        
        Note: The built-in invite code 'hdu340' is always valid (case-insensitive)
        and assigns the item_manager role without database validation.
        
        Args:
            invite_code: Invite code for registration
            username: Desired username
            password: User password
            phone: Optional phone number
            email: Optional email address
            department: Optional department name
        
        Returns:
            Created User instance
        
        Raises:
            ValidationError: If invite code is invalid or username already exists
        """
        with transaction.atomic():
            # Check for built-in permanent invite code (case-insensitive)
            if invite_code.lower() == self.BUILTIN_INVITE_CODE:
                default_role = self.BUILTIN_INVITE_CODE_ROLE
                validated_invite_code = None
            else:
                # Validate and use invite code from database (this also locks the row)
                validated_invite_code = self.invite_code_service.validate_and_use(invite_code)
                default_role = validated_invite_code.default_role
            
            # Validate username uniqueness
            if User.objects.filter(username=username).exists():
                raise ValidationError({
                    'username': 'This username is already taken.'
                })
            
            # Validate phone uniqueness if provided
            if phone and User.objects.filter(phone=phone).exists():
                raise ValidationError({
                    'phone': 'This phone number is already registered.'
                })
            
            # Create user with role from invite code
            user = User.objects.create_user(
                username=username,
                password=password,
                phone=phone,
                email=email,
                department=department or '',
                role=default_role,
                is_active=True
            )
            
            # Create audit log for invite code usage (only for database codes)
            if validated_invite_code:
                self._log_invite_use(
                    invite_code=validated_invite_code,
                    user=user
                )
            
            return user
