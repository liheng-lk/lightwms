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


class AuditLog(models.Model):
    """
    Audit log model for recording all data modifications.
    
    This model is immutable - records cannot be updated or deleted
    once created. This is enforced at the model layer.
    
    Attributes:
        action: The type of action performed
        target_type: The type of resource affected
        target_id: The ID of the affected resource
        diff: JSON containing {before: {...}, after: {...}}
        operator: The user who performed the action
        operator_role: The role of the operator at the time of action
        ip: Client IP address
        user_agent: Client user agent string
        created_at: Timestamp of the action
    """
    
    # Action performed
    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices,
    )
    
    # Target resource
    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
    )
    target_id = models.PositiveIntegerField()
    
    # Change details (before/after state)
    diff = models.JSONField(default=dict)
    
    # Operator information
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    operator_role = models.CharField(max_length=20, blank=True, default='')
    
    # Client information
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')
    
    # Timestamp
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
        """
        Override save to prevent updates.
        AuditLog records are immutable once created.
        """
        if self.pk:
            raise PermissionError("AuditLog records cannot be updated")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        Override delete to prevent deletion.
        AuditLog records are immutable.
        """
        raise PermissionError("AuditLog records cannot be deleted")


class LoginLog(models.Model):
    """
    Login log model for recording authentication events.
    
    Records both successful and failed login attempts,
    as well as logout events.
    """
    
    # Username attempted (stored even for failed logins where user doesn't exist)
    username_attempted = models.CharField(max_length=150)
    
    # User reference (null for failed logins with non-existent username)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_logs'
    )
    
    # Login result
    success = models.BooleanField()
    
    # Client information
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_loginlog'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        status = 'success' if self.success else 'failed'
        return f"{self.username_attempted} - {status} - {self.created_at}"
