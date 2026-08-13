"""Role utility functions for LightWMS."""
from typing import Optional, Any


def _is_authenticated(user: Optional[Any]) -> bool:
    return bool(user is not None and getattr(user, 'is_authenticated', False))


def is_super_admin(user: Optional[Any]) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, 'is_super_admin', False))


def is_item_manager(user: Optional[Any]) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, 'is_item_manager', False))


def is_read_only_user(user: Optional[Any]) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, 'is_read_only_user', False))


def can_manage_item(user: Optional[Any], item: Any) -> bool:
    """
    Super Admin can manage any item; Item Manager can manage only owned items.
    Ordinary users never mutate inventory.
    """
    if is_super_admin(user):
        return True
    if is_item_manager(user):
        return getattr(item, 'owner_id', None) == getattr(user, 'id', None)
    return False
