"""History-safe user deletion for LightWMS."""
from __future__ import annotations

from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, TargetType
from ..models import User


class UserDeletionConflict(Exception):
    """Backward-compatible exception kept for API imports."""

    def __init__(self, protected_models: list[str] | None = None):
        self.protected_models = protected_models or []
        super().__init__('该用户关联业务历史，已改用历史安全删除策略。')


class UserDeletionService:
    """Remove an account while preserving historical business records."""

    def delete_user(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = '',
    ) -> tuple[int, str, bool]:
        """
        Delete an unused account physically; archive referenced accounts.

        Returns ``(target_id, username, archived)``.  An archived account is
        disabled, hidden from user management and has all tokens invalidated,
        while foreign keys from invoices/inventory/ledgers keep pointing at the
        historical account row.
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            if user.id == operator.id:
                raise ValueError('不能删除当前登录的超级管理员账户')
            if user.deleted_at is not None:
                raise User.DoesNotExist

            target_id = user.id
            username = user.username
            snapshot = {
                'username': user.username,
                'role': user.role,
                'is_active': user.is_active,
                'email': user.email or '',
                'department': user.department or '',
            }

            archived = False
            try:
                # Use an inner savepoint: ProtectedError must not poison the
                # outer transaction because we may need to archive instead.
                with transaction.atomic():
                    user.delete()
            except ProtectedError:
                archived = True
                now = timezone.now().replace(microsecond=0)
                user.is_active = False
                user.deleted_at = now
                user.tokens_invalid_before = now
                user.must_change_password = False
                user.phone = None
                user.wechat_openid = None
                user.set_unusable_password()
                user.save(update_fields=[
                    'is_active', 'deleted_at', 'tokens_invalid_before',
                    'must_change_password', 'phone', 'wechat_openid', 'password',
                    'updated_at',
                ])

            AuditLog.objects.create(
                action=AuditAction.DELETE,
                target_type=TargetType.USER,
                target_id=target_id,
                diff={
                    'before': snapshot,
                    'after': {
                        'archived': True,
                        'is_active': False,
                    } if archived else None,
                },
                operator=operator,
                operator_role=operator.role,
                ip=ip or None,
                user_agent=user_agent,
            )
            return target_id, username, archived
