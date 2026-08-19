"""Guarded permanent user deletion for LightWMS."""
from __future__ import annotations

from django.db import transaction
from django.db.models.deletion import ProtectedError

from apps.audit.models import AuditAction, AuditLog, TargetType
from ..models import User


class UserDeletionConflict(Exception):
    """Raised when business records protect a user from permanent deletion."""

    def __init__(self, protected_models: list[str] | None = None):
        self.protected_models = protected_models or []
        message = (
            '该用户仍关联库存责任或业务历史，不能永久删除。'
            '请先转移物品/库位责任；如存在历史业务记录，请禁用该用户以保留台账。'
        )
        super().__init__(message)


class UserDeletionService:
    """Delete unused user accounts without damaging inventory/history."""

    def delete_user(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = '',
    ) -> tuple[int, str]:
        """Permanently delete an unreferenced user and retain an audit snapshot."""
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=user_id)
                if user.id == operator.id:
                    raise ValueError('不能删除当前登录的超级管理员账户')

                target_id = user.id
                username = user.username
                snapshot = {
                    'username': user.username,
                    'role': user.role,
                    'is_active': user.is_active,
                    'email': user.email or '',
                    'department': user.department or '',
                }

                # Django PROTECT relations are intentional in LightWMS: ownership
                # and ledger history must never disappear with an account.
                user.delete()

                AuditLog.objects.create(
                    action=AuditAction.DELETE,
                    target_type=TargetType.USER,
                    target_id=target_id,
                    diff={'before': snapshot, 'after': None},
                    operator=operator,
                    operator_role=operator.role,
                    ip=ip or None,
                    user_agent=user_agent,
                )
                return target_id, username
        except ProtectedError as exc:
            protected_models = sorted({
                obj._meta.verbose_name for obj in exc.protected_objects
            })
            raise UserDeletionConflict(protected_models) from exc
