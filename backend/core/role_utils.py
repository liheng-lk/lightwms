"""
Role utility functions for LightWMS.

This module provides safe role checking functions that work with the User model's
properties instead of string comparisons. This ensures consistency and avoids
bugs from typos or case mismatches.

Usage:
    from core.role_utils import is_super_admin, is_item_manager
    
    if is_super_admin(user):
        # Super admin logic
    
    if is_item_manager(user):
        # Item manager logic
"""
from typing import Optional, Any


def is_super_admin(user: Optional[Any]) -> bool:
    """
    Check if user is a Super Admin.
    
    Uses the User model's is_super_admin property for safe comparison.
    
    Args:
        user: User object or None
        
    Returns:
        True if user is authenticated and has super_admin role
    """
    if user is None:
        return False
    if not getattr(user, 'is_authenticated', False):
        return False
    return getattr(user, 'is_super_admin', False)


def is_item_manager(user: Optional[Any]) -> bool:
    """
    Check if user is an Item Manager.
    
    Uses the User model's is_item_manager property for safe comparison.
    
    Args:
        user: User object or None
        
    Returns:
        True if user is authenticated and has item_manager role
    """
    if user is None:
        return False
    if not getattr(user, 'is_authenticated', False):
        return False
    return getattr(user, 'is_item_manager', False)


def can_manage_item(user: Optional[Any], item: Any) -> bool:
    """
    Check if user can manage (update/delete) an item.
    
    Super Admin can manage any item.
    Item Manager can manage any item.
    
    Args:
        user: User object or None
        item: Item object with owner_id attribute
        
    Returns:
        True if user can manage the item
    """
    if is_super_admin(user):
        return True
    if is_item_manager(user):
        return True
    return False
