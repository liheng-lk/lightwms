"""
User models for LightWMS.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UserRole(models.TextChoices):
    """User role enumeration."""
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    ITEM_MANAGER = 'item_manager', 'Item Manager'
    READ_ONLY_USER = 'read_only_user', '普通用户'


class UserManager(BaseUserManager):
    """Custom user manager for User model."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.READ_ONLY_USER)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    """Custom LightWMS user."""

    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, default='')
    wechat_openid = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.READ_ONLY_USER
    )
    must_change_password = models.BooleanField(default=False)
    tokens_invalid_before = models.DateTimeField(blank=True, null=True)
    # Accounts referenced by business history are archived instead of physically
    # deleted so invoices, ownership and ledgers keep their historical author.
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    class Meta:
        db_table = 'users_user'
        constraints = [
            models.UniqueConstraint(
                fields=['wechat_openid'],
                condition=Q(wechat_openid__isnull=False),
                name='uq_user_wechat_openid_not_null',
            ),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def invalidate_tokens(self):
        self.tokens_invalid_before = timezone.now().replace(microsecond=0)
        self.save(update_fields=['tokens_invalid_before'])

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_item_manager(self):
        return self.role == UserRole.ITEM_MANAGER

    @property
    def is_read_only_user(self):
        return self.role == UserRole.READ_ONLY_USER


class InviteCodeStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    EXHAUSTED = 'exhausted', 'Exhausted'
    EXPIRED = 'expired', 'Expired'
    DISABLED = 'disabled', 'Disabled'


class InviteCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    max_uses = models.PositiveIntegerField(default=1)
    current_uses = models.PositiveIntegerField(default=0)
    default_role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.READ_ONLY_USER
    )
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invite_codes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_invitecode'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(current_uses__lte=models.F('max_uses')),
                name='ck_invite_current_uses_lte_max_uses',
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.status})"

    @property
    def status(self) -> str:
        if not self.is_active:
            return InviteCodeStatus.DISABLED
        if self.expires_at and timezone.now() > self.expires_at:
            return InviteCodeStatus.EXPIRED
        if self.current_uses >= self.max_uses:
            return InviteCodeStatus.EXHAUSTED
        return InviteCodeStatus.ACTIVE

    @property
    def is_usable(self) -> bool:
        return self.status == InviteCodeStatus.ACTIVE

    @property
    def remaining_uses(self) -> int:
        return max(0, self.max_uses - self.current_uses)


class WechatOAuthState(models.Model):
    """One-time CSRF state issued before a WeChat OAuth callback."""

    state = models.CharField(max_length=100, unique=True)
    redirect_uri = models.CharField(max_length=500, blank=True, default='')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_wechatoauthstate'
        indexes = [models.Index(fields=['expires_at'])]

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class WechatSession(models.Model):
    session_id = models.CharField(max_length=64, unique=True)
    openid = models.CharField(max_length=100)
    unionid = models.CharField(max_length=100, blank=True, null=True)
    nickname = models.CharField(max_length=100, blank=True, default='')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_wechatsession'
        indexes = [models.Index(fields=['expires_at'])]

    def __str__(self):
        return f"WechatSession {self.session_id[:8]}..."

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
