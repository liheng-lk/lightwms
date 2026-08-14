"""RBAC permission classes for LightWMS."""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.role_utils import is_super_admin, is_item_manager, is_read_only_user


class IsSuperAdmin(BasePermission):
    """Super Admin only."""

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class IsItemManagerOrSuperAdmin(BasePermission):
    """Inventory-management role or Super Admin."""

    def has_permission(self, request, view):
        return is_super_admin(request.user) or is_item_manager(request.user)


class IsOrdinaryUser(BasePermission):
    """Ordinary warehouse user only."""

    def has_permission(self, request, view):
        return is_read_only_user(request.user)


class IsAuthenticatedInventoryAccess(BasePermission):
    """
    Authenticated users may read inventory; only managers/admins may mutate it.

    This is the default permission boundary for inventory master-data endpoints.
    """

    def has_permission(self, request, view):
        if not getattr(request.user, 'is_authenticated', False):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_super_admin(request.user) or is_item_manager(request.user)


class IsItemOwner(BasePermission):
    """Inventory management access for Item Manager or Super Admin.

    The historic class name is retained for compatibility, but Item ownership
    is responsibility metadata rather than a role authorization boundary.
    """

    def has_object_permission(self, request, view, obj):
        if not getattr(request.user, 'is_authenticated', False):
            return False
        return is_super_admin(request.user) or is_item_manager(request.user)


class IsReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class CanBorrowReturn(BasePermission):
    """
    Borrow: Item Manager or Super Admin.
    Return: Item Manager, Super Admin, or the current borrower.
    """

    def has_object_permission(self, request, view, obj):
        if not getattr(request.user, 'is_authenticated', False):
            return False

        user = request.user
        if is_super_admin(user) or is_item_manager(user):
            return True

        if getattr(view, 'action', None) == 'return_item':
            active_borrows = getattr(obj, 'borrow_records', None)
            if active_borrows:
                return active_borrows.filter(
                    status='active', borrower_id=user.id
                ).exists()

        return False
