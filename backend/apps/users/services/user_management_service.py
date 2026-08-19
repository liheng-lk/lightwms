"""User management service for LightWMS."""
import secrets
import string

from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog, AuditAction, TargetType
from ..models import User


class UserManagementService:
    """User lifecycle operations with audit logging and session invalidation."""

    @staticmethod
    def _invalidate_sessions(user: User) -> None:
        """Invalidate all JWTs issued before this security-sensitive change."""
        user.tokens_invalid_before = timezone.now().replace(microsecond=0)

    @staticmethod
    def _managed_user(user_id: int, *, for_update: bool = False) -> User:
        """Return a non-deleted user; retired accounts cannot be revived via admin APIs."""
        queryset = User.objects.filter(deleted_at__isnull=True)
        if for_update:
            queryset = queryset.select_for_update()
        return queryset.get(pk=user_id)

    @staticmethod
    def _audit(
        *, action: str, user: User, operator: User, before: dict | None,
        after: dict | None, ip: str = '', user_agent: str = ''
    ) -> None:
        AuditLog.objects.create(
            action=action,
            target_type=TargetType.USER,
            target_id=user.id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=operator.role,
            ip=ip,
            user_agent=user_agent,
        )

    def disable_user(self, user_id: int, operator: User, ip: str = '', user_agent: str = '') -> User:
        with transaction.atomic():
            user = self._managed_user(user_id, for_update=True)
            if user.id == operator.id:
                raise ValueError('Cannot disable your own account')

            before = {
                'is_active': user.is_active,
                'tokens_invalid_before': user.tokens_invalid_before.isoformat() if user.tokens_invalid_before else None,
            }
            user.is_active = False
            self._invalidate_sessions(user)
            user.save(update_fields=['is_active', 'tokens_invalid_before', 'updated_at'])
            self._audit(
                action=AuditAction.DEACTIVATE,
                user=user,
                operator=operator,
                before=before,
                after={
                    'is_active': False,
                    'tokens_invalid_before': user.tokens_invalid_before.isoformat(),
                },
                ip=ip,
                user_agent=user_agent,
            )
            return user

    def reset_password(self, user_id: int, operator: User, ip: str = '', user_agent: str = '') -> tuple[User, str]:
        with transaction.atomic():
            user = self._managed_user(user_id, for_update=True)
            before = {
                'must_change_password': user.must_change_password,
                'tokens_invalid_before': user.tokens_invalid_before.isoformat() if user.tokens_invalid_before else None,
            }
            temp_password = self._generate_temp_password()
            user.set_password(temp_password)
            user.must_change_password = True
            self._invalidate_sessions(user)
            user.save(update_fields=['password', 'must_change_password', 'tokens_invalid_before', 'updated_at'])
            self._audit(
                action=AuditAction.UPDATE,
                user=user,
                operator=operator,
                before=before,
                after={
                    'must_change_password': True,
                    'tokens_invalid_before': user.tokens_invalid_before.isoformat(),
                    'password_reset': True,
                },
                ip=ip,
                user_agent=user_agent,
            )
            return user, temp_password

    def list_users(self, role: str = None, is_active: bool = None, date_from=None, date_to=None):
        queryset = User.objects.filter(deleted_at__isnull=True).order_by('-created_at', '-id')
        if role is not None:
            queryset = queryset.filter(role=role)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if date_from is not None:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to is not None:
            queryset = queryset.filter(created_at__lte=date_to)
        return queryset

    def _generate_temp_password(self, length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice('!@#$%^&*'),
        ]
        password.extend(secrets.choice(alphabet) for _ in range(length - 4))
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)

    def create_user(
        self, username: str, password: str, role: str, operator: User,
        phone: str = None, email: str = None, department: str = None,
        ip: str = '', user_agent: str = ''
    ) -> User:
        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                raise ValueError('用户名已存在')
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role,
                phone=phone or None,
                email=email or '',
                department=department or '',
                is_active=True,
                must_change_password=False,
            )
            self._audit(
                action=AuditAction.CREATE,
                user=user,
                operator=operator,
                before=None,
                after={
                    'username': user.username,
                    'role': user.role,
                    'is_active': user.is_active,
                },
                ip=ip,
                user_agent=user_agent,
            )
            return user

    def change_password(
        self, user: User, old_password: str, new_password: str,
        ip: str = '', user_agent: str = ''
    ) -> User:
        with transaction.atomic():
            locked_user = self._managed_user(user.pk, for_update=True)
            if not check_password(old_password, locked_user.password):
                raise ValueError('当前密码不正确')

            locked_user.set_password(new_password)
            locked_user.must_change_password = False
            self._invalidate_sessions(locked_user)
            locked_user.save(update_fields=[
                'password', 'must_change_password', 'tokens_invalid_before', 'updated_at'
            ])
            self._audit(
                action=AuditAction.UPDATE,
                user=locked_user,
                operator=locked_user,
                before=None,
                after={
                    'password_changed': True,
                    'must_change_password': False,
                    'sessions_invalidated': True,
                },
                ip=ip,
                user_agent=user_agent,
            )
            return locked_user

    def admin_set_password(
        self, user_id: int, new_password: str, operator: User,
        ip: str = '', user_agent: str = ''
    ) -> User:
        with transaction.atomic():
            user = self._managed_user(user_id, for_update=True)
            user.set_password(new_password)
            user.must_change_password = False
            self._invalidate_sessions(user)
            user.save(update_fields=[
                'password', 'must_change_password', 'tokens_invalid_before', 'updated_at'
            ])
            self._audit(
                action=AuditAction.UPDATE,
                user=user,
                operator=operator,
                before=None,
                after={
                    'password_set_by_admin': True,
                    'must_change_password': False,
                    'sessions_invalidated': True,
                },
                ip=ip,
                user_agent=user_agent,
            )
            return user

    def enable_user(self, user_id: int, operator: User, ip: str = '', user_agent: str = '') -> User:
        with transaction.atomic():
            user = self._managed_user(user_id, for_update=True)
            before = {'is_active': user.is_active}
            user.is_active = True
            user.save(update_fields=['is_active', 'updated_at'])
            self._audit(
                action=AuditAction.UPDATE,
                user=user,
                operator=operator,
                before=before,
                after={'is_active': True},
                ip=ip,
                user_agent=user_agent,
            )
            return user

    def update_user_role(
        self, user_id: int, new_role: str, operator: User,
        ip: str = '', user_agent: str = ''
    ) -> User:
        with transaction.atomic():
            user = self._managed_user(user_id, for_update=True)
            if user.id == operator.id:
                raise ValueError('不能修改自己的角色')

            before = {
                'role': user.role,
                'tokens_invalid_before': user.tokens_invalid_before.isoformat() if user.tokens_invalid_before else None,
            }
            user.role = new_role
            self._invalidate_sessions(user)
            user.save(update_fields=['role', 'tokens_invalid_before', 'updated_at'])
            self._audit(
                action=AuditAction.UPDATE,
                user=user,
                operator=operator,
                before=before,
                after={
                    'role': user.role,
                    'tokens_invalid_before': user.tokens_invalid_before.isoformat(),
                    'sessions_invalidated': True,
                },
                ip=ip,
                user_agent=user_agent,
            )
            return user
