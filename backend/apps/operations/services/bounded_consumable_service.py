"""Numeric-boundary wrapper for consumable stock operations."""
from typing import Optional

from django.db import transaction

from apps.inventory.models import Item
from apps.users.models import User
from core.exceptions import BusinessConflictError

from .consumable_service import ConsumableService as BaseConsumableService


MAX_DB_QUANTITY = 2_147_483_647


class BoundedConsumableService(BaseConsumableService):
    """Keep Item.quantity within PostgreSQL PositiveIntegerField bounds."""

    @classmethod
    @transaction.atomic
    def replenish(
        cls,
        item_id: int,
        quantity: int,
        notes: str,
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = '',
    ):
        # Lock before checking the sum. This is important: two concurrent
        # replenishments must not both pass an unlocked preflight and then push
        # the stored integer beyond the database limit.
        item = Item.objects.select_for_update().get(id=item_id)

        if quantity > 0 and item.quantity > MAX_DB_QUANTITY - quantity:
            raise BusinessConflictError(
                code='QUANTITY_OVERFLOW',
                message='Replenishment would exceed the maximum supported inventory quantity.',
                details={
                    'item_id': item.id,
                    'current_quantity': item.quantity,
                    'requested': quantity,
                    'maximum': MAX_DB_QUANTITY,
                },
            )

        # Base service executes inside this same transaction. Its second
        # select_for_update is safe and keeps all existing validation/auditing.
        return super().replenish(
            item_id=item_id,
            quantity=quantity,
            notes=notes,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
