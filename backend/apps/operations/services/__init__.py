"""
Operations services for LightWMS.

``BorrowService`` is exported as the quantity-aware implementation. The legacy
class in ``borrow_service.py`` assumes one active borrow per item and picks an
arbitrary record on return, which is wrong since migration 0004 allowed
multiple active borrows; it is kept only as the base class.
"""
from .quantity_borrow_service import QuantityBorrowService
from .quantity_borrow_service import QuantityBorrowService as BorrowService
from .bounded_consumable_service import BoundedConsumableService as ConsumableService

__all__ = ['BorrowService', 'QuantityBorrowService', 'ConsumableService']
