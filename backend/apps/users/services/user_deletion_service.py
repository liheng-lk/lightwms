"""Safe user deletion for LightWMS.

User rows referenced by inventory or ledger history cannot be physically deleted
without damaging traceability.  A Super Admin deletion therefore retires the
account: authentication is disabled, tokens are invalidated and sensitive
contact/OAuth fields are cleared, while the row remains as the immutable target
of historical foreign keys.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, TargetType
from ..models import User


class UserDeletionService:
    """Retire a user account without deleting business history."""

    def delete_user(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = '',
    ) -> tuple[int, str]:
        """Soft-delete a user and retain a complete audit snapshot."""
        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(deleted_at__isnull=True)
                .get(pk=user_id)
            )
            if user.id == operator.id:
                raise ValueError('不能删除当前登录的超级管理员账户')

            target_id = user.id
            username = user.username
            snapshot = {
                'username': user.username,
                'role': user.role,
                'is_active': user.is_active,
                'email': user.email or '',
                'phone': user.phone or '',
                'department': user.department or '',
                'wechat_openid_present': bool(user.wechat_openid),
            }

            now = timezone.now()
            user.is_active = False
            user.deleted_at = now
            user.tokens_invalid_before = now.replace(microsecond=0)
            user.must_change_password = False
            user.set_unusable_password()

            # Keep username for historical attribution (invoice uploader,
            # borrower/operator display etc.), but remove contact/OAuth data.
            user.email = ''
            user.phone = None
            user.department = ''
            user.wechat_openid = None
            user.first_name = ''
            user.last_name = ''
            user.save(update_fields=[
                'is_active',
                'deleted_at',
                'tokens_invalid_before',
                'must_change_password',
                'password',
                'email',
                'phone',
                'department',
                'wechat_openid',
                'first_name',
                'last_name',
                'updated_at',
            ])

            AuditLog.objects.create(
                action=AuditAction.DELETE,
                target_type=TargetType.USER,
                target_id=target_id,
                diff={
                    'before': snapshot,
                    'after': {
                        'username': username,
                        'is_active': False,
                        'deleted_at': now.isoformat(),
                        'account_retired': True,
                    },
                },
                operator=operator,
                operator_role=operator.role,
                ip=ip or None,
                user_agent=user_agent,
            )
            return target_id, username
