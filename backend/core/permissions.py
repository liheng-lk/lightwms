"""
RBAC Permission classes for LightWMS.

Uses User model properties (is_super_admin, is_item_manager, is_read_only_user)
for role checks instead of string comparisons to avoid typos and case issues.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.role_utils import is_super_admin, is_item_manager


class IsSuperAdmin(BasePermission):
    """Permission class for Super Admin only access."""
    
    def has_permission(self, request, view):
        return is_super_admin(request.user)


class IsItemManagerOrSuperAdmin(BasePermission):
    """Permission class for Item Manager or Super Admin access."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return is_super_admin(request.user) or is_item_manager(request.user)


class IsItemOwner(BasePermission):
    """Permission class for item owner or Super Admin."""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if is_super_admin(request.user):
            return True
        return getattr(obj, 'owner_id', None) == request.user.id


class IsReadOnly(BasePermission):
    """Permission class for read-only access."""
    
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class CanBorrowReturn(BasePermission):
    """
    Permission class for borrow/return operations.
    - Owner and Super Admin can borrow
    - Owner, Super Admin, and current borrower can return
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        user = request.user
        
        # Super Admin can do anything
        if is_super_admin(user):
            return True
        
        # Owner can borrow and return
        if getattr(obj, 'owner_id', None) == user.id:
            return True
        
        # For return action, check if user is the current borrower
        if getattr(view, 'action', None) == 'return_item':
            active_borrow = getattr(obj, 'borrow_records', None)
            if active_borrow:
                active_record = active_borrow.filter(status='active').first()
                if active_record and active_record.borrower_id == user.id:
                    return True
        
        return False
