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
    Super Admin and Item Manager can manage inventory globally.
    Ordinary users never mutate inventory.

    ``item.owner`` is inventory metadata/responsibility information; it is not
    an authorization boundary for the Item Manager role.
    """
    return is_super_admin(user) or is_item_manager(user)
