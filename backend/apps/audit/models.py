"""
Audit models for LightWMS.
Contains LoginLog for authentication events and AuditLog for data changes.
"""
from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    """Audit action enumeration."""
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    DEACTIVATE = 'deactivate', 'Deactivate'
    BORROW = 'borrow', 'Borrow'
    RETURN = 'return', 'Return'
    TAKE = 'take', 'Take'
    REPLENISH = 'replenish', 'Replenish'
    INVITE_USE = 'invite_use', 'Invite Use'
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'
    IMPORT = 'import', 'Import'
    EXPORT = 'export', 'Export'


class TargetType(models.TextChoices):
    """Audit target type enumeration."""
    ITEM = 'Item', 'Item'
    CATEGORY = 'Category', 'Category'
    LOCATION = 'Location', 'Location'
    WAREHOUSE = 'Warehouse', 'Warehouse'
    INVITE_CODE = 'InviteCode', 'Invite Code'
    USER = 'User', 'User'
    BORROW_RECORD = 'BorrowRecord', 'Borrow Record'
    TAKE_RECORD = 'TakeRecord', 'Take Record'
    REPLENISH_RECORD = 'ReplenishRecord', 'Replenish Record'
    ITEM_IMAGE = 'ItemImage', 'Item Image'
    INVOICE = 'Invoice', 'Invoice'
    SYSTEM = 'System', 'System Setting'


class AuditLog(models.Model):
    """
    Audit log model for recording all data modifications.

    Audit rows are immutable after creation. This is enforced both at the
    model instance layer and, on PostgreSQL, by migration 0003's database
    trigger so QuerySet/bulk mutation paths cannot bypass the contract.
    """

    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices,
    )

    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
    )
    # Business models use BigAutoField, so audit references must be capable of
    # recording the same identifier range. System-level settings use target 0.
    target_id = models.PositiveBigIntegerField()

    diff = models.JSONField(default=dict)

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    operator_role = models.CharField(max_length=20, blank=True, default='')

    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_auditlog'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['operator', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.action} {self.target_type}:{self.target_id} by {self.operator_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("AuditLog records cannot be updated")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog records cannot be deleted")


class LoginLog(models.Model):
    """
    Login log model for recording authentication events.

    Records both successful and failed login attempts,
    as well as logout events.
    """

    username_attempted = models.CharField(max_length=150)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_logs'
    )
    success = models.BooleanField()
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_loginlog'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        status = 'success' if self.success else 'failed'
        return f"{self.username_attempted} - {status} - {self.created_at}"
