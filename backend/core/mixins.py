"""
Mixins for ViewSets in LightWMS.

Uses User model properties (is_super_admin, is_item_manager, is_read_only_user)
for role checks instead of string comparisons to avoid typos and case issues.
"""
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from core.role_utils import is_super_admin, is_item_manager


class DataIsolationMixin:
    """
    Mixin for ViewSets to implement data-level filtering based on user role.
    
    Data isolation rules:
    - Super_Admin: full dataset (no filtering)
    - Item_Manager: owner-scoped dataset (only owned items and related records)
    - Read_Only_User: full dataset (read-only enforced by permissions, not data isolation)
    
    Note: Read_Only_User doesn't have data isolation, only permission control.
    
    Security: Both "not found" and "no permission" return 404 to prevent
    information leakage about resource existence.
    
    IMPORTANT: All @action methods MUST use self.get_object() to retrieve resources.
    Direct Model.objects.get() queries are forbidden as they bypass data isolation.
    """
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        All @action methods must use self.get_object() which calls this method.
        """
        qs = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return qs.none()
        
        # Super Admin sees everything
        if is_super_admin(user):
            return qs
        
        # Item Manager sees only their own data
        if is_item_manager(user):
            # Direct owner field
            if hasattr(qs.model, 'owner_id'):
                return qs.filter(owner_id=user.id)
            # Related through item (for records)
            if hasattr(qs.model, 'item'):
                return qs.filter(item__owner_id=user.id)
        
        # Read Only User sees everything (permission controls write access)
        return qs
    
    def get_object(self):
        """
        Get object from filtered queryset.
        Returns 404 for both "not found" and "no permission" (security best practice).
        
        This method:
        1. Gets the filtered queryset (applies data isolation)
        2. Applies any additional filters from filter_queryset
        3. Retrieves the object or raises 404
        4. Checks object permissions, converting PermissionDenied to 404
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get lookup field
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        
        try:
            obj = queryset.get(**filter_kwargs)
        except queryset.model.DoesNotExist:
            raise Http404
        
        # Check object permissions - convert PermissionDenied to 404
        # This prevents information leakage about resource existence
        try:
            self.check_object_permissions(self.request, obj)
        except PermissionDenied:
            raise Http404
        
        return obj
    
    def check_object_permissions(self, request, obj):
        """
        Check object-level permissions.
        
        Note: When called from get_object(), PermissionDenied is caught
        and converted to Http404 for security.
        """
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None)
                )
