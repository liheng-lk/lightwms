"""
Admin configuration for audit app.
AuditLog is read-only in admin - no add, change, or delete allowed.
"""
from django.contrib import admin
from .models import AuditLog, LoginLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin for AuditLog - completely read-only.
    No add, change, or delete operations are permitted.
    """
    list_display = [
        'id', 'action', 'target_type', 'target_id',
        'operator', 'operator_role', 'ip', 'created_at'
    ]
    list_filter = ['action', 'target_type', 'operator_role', 'created_at']
    search_fields = ['target_id', 'ip', 'operator__username']
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent adding AuditLog records via admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent changing AuditLog records via admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting AuditLog records via admin."""
        return False


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """
    Admin for LoginLog - read-only.
    """
    list_display = [
        'id', 'username_attempted', 'user', 'success',
        'ip', 'created_at'
    ]
    list_filter = ['success', 'created_at']
    search_fields = ['username_attempted', 'ip', 'user__username']
    readonly_fields = [f.name for f in LoginLog._meta.fields]
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent adding LoginLog records via admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent changing LoginLog records via admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting LoginLog records via admin."""
        return False
