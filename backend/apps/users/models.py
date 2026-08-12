"""
User models for LightWMS.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    """User role enumeration."""
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    ITEM_MANAGER = 'item_manager', 'Item Manager'
    READ_ONLY_USER = 'read_only_user', '普通用户'


class UserManager(BaseUserManager):
    """Custom user manager for User model."""
    
    def create_user(self, username, password=None, **extra_fields):
        """Create and return a regular user."""
        if not username:
            raise ValueError('Username is required')
        
        extra_fields.setdefault('is_active', True)
        # Least-privilege default: a newly created regular account must never
        # silently receive inventory-management permissions.
        extra_fields.setdefault('role', UserRole.READ_ONLY_USER)
        
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for LightWMS.
    
    Extends Django's AbstractUser with additional fields for:
    - Phone and department information
    - WeChat OpenID for OAuth integration
    - Role-based access control
    - Token invalidation support
    - Password change enforcement
    """
    
    # Override email to make it optional
    email = models.EmailField(blank=True, null=True)
    
    # Contact information
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, default='')
    
    # WeChat OAuth integration
    wechat_openid = models.CharField(max_length=100, blank=True, null=True)
    
    # Role-based access control
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.READ_ONLY_USER
    )
    
    # Password management
    must_change_password = models.BooleanField(default=False)
    
    # Token invalidation - all tokens issued before this time are invalid
    # Used when disabling user or forcing logout
    tokens_invalid_before = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users_user'
        indexes = [
            # Partial unique index on wechat_openid (only for non-null values)
            # This is created via migration with RunSQL
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def invalidate_tokens(self):
        """
        Invalidate all tokens issued before now.
        Aligns to second precision to avoid microsecond edge cases.
        """
        self.tokens_invalid_before = timezone.now().replace(microsecond=0)
        self.save(update_fields=['tokens_invalid_before'])
    
    @property
    def is_super_admin(self):
        """Check if user is a super admin."""
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_item_manager(self):
        """Check if user is an item manager."""
        return self.role == UserRole.ITEM_MANAGER

    @property
    def is_read_only_user(self):
        """Check if user is an ordinary read-only warehouse user."""
        return self.role == UserRole.READ_ONLY_USER


class InviteCodeStatus(models.TextChoices):
    """Computed status for invite codes."""
    ACTIVE = 'active', 'Active'
    EXHAUSTED = 'exhausted', 'Exhausted'
    EXPIRED = 'expired', 'Expired'
    DISABLED = 'disabled', 'Disabled'


class InviteCode(models.Model):
    """
    Invite code model for user registration.
    
    Invite codes are used to control new user registration.
    Each code has a maximum number of uses, an optional expiration date,
    and a default role to assign to new users.
    """
    
    # Unique code in format INV-XXXXXX
    code = models.CharField(max_length=20, unique=True)
    
    # Usage limits
    max_uses = models.PositiveIntegerField(default=1)
    current_uses = models.PositiveIntegerField(default=0)
    
    # Default role for users registered with this code
    default_role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.READ_ONLY_USER
    )
    
    # Expiration (optional)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Active status (can be disabled by admin)
    is_active = models.BooleanField(default=True)
    
    # Creator reference
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invite_codes'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users_invitecode'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.code} ({self.status})"
    
    @property
    def status(self) -> str:
        """
        Compute the current status of the invite code.
        
        Priority order:
        1. disabled (is_active=false)
        2. expired (now > expires_at)
        3. exhausted (current_uses >= max_uses)
        4. active
        
        Returns:
            InviteCodeStatus value
        """
        if not self.is_active:
            return InviteCodeStatus.DISABLED
        
        if self.expires_at and timezone.now() > self.expires_at:
            return InviteCodeStatus.EXPIRED
        
        if self.current_uses >= self.max_uses:
            return InviteCodeStatus.EXHAUSTED
        
        return InviteCodeStatus.ACTIVE
    
    @property
    def is_usable(self) -> bool:
        """Check if the invite code can be used for registration."""
        return self.status == InviteCodeStatus.ACTIVE
    
    @property
    def remaining_uses(self) -> int:
        """Get the number of remaining uses."""
        return max(0, self.max_uses - self.current_uses)


class WechatSession(models.Model):
    """
    Temporary session for WeChat OAuth flow.
    
    Stores the WeChat openid temporarily during the registration process
    before the user completes registration with an invite code.
    """
    
    # Session identifier
    session_id = models.CharField(max_length=64, unique=True)
    
    # WeChat openid from OAuth callback
    openid = models.CharField(max_length=100)
    
    # Optional additional info from WeChat
    unionid = models.CharField(max_length=100, blank=True, null=True)
    nickname = models.CharField(max_length=100, blank=True, default='')
    
    # Expiration (sessions are short-lived)
    expires_at = models.DateTimeField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users_wechatsession'
        indexes = [
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"WechatSession {self.session_id[:8]}..."
    
    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return timezone.now() > self.expires_at
