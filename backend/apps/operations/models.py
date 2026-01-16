"""
Operations models for LightWMS.

This module contains models for:
- BorrowRecord: Records for reusable item borrowing/returning
- TakeRecord: Records for consumable item taking
- ReplenishRecord: Records for consumable item replenishment
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class BorrowStatus(models.TextChoices):
    """Stored status for borrow records."""
    ACTIVE = 'active', 'Active'
    RETURNED = 'returned', 'Returned'


class BorrowComputedStatus(models.TextChoices):
    """Computed status for API output."""
    ACTIVE = 'active', 'Active'
    OVERDUE = 'overdue', 'Overdue'
    RETURNED = 'returned', 'Returned'


class BorrowRecord(models.Model):
    """
    Borrow record model for tracking reusable item borrowing.
    
    Records the borrowing and returning of reusable items.
    Each active borrow creates a record with status='active'.
    When returned, the record is updated with actual_return_datetime
    and status='returned'.
    
    Constraints:
    - Only one active borrow per item (partial unique index: uq_borrow_active_item)
    - Borrower must be a system user
    
    Computed status (for API output):
    - 'returned': actual_return_datetime is not null
    - 'overdue': status='active' AND today > expected_return_date
    - 'active': otherwise
    """
    
    # The item being borrowed
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        related_name='borrow_records'
    )
    
    # The user who borrowed the item
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='borrowed_records'
    )
    
    # The user who registered the borrow operation
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operated_borrow_records'
    )
    
    # Quantity borrowed (default 1 for backward compatibility)
    quantity = models.PositiveIntegerField(default=1)
    
    # Expected return date
    expected_return_date = models.DateField()
    
    # Actual return datetime (null until returned)
    actual_return_datetime = models.DateTimeField(null=True, blank=True)
    
    # Notes for borrowing
    notes = models.TextField(blank=True, default='')
    
    # Notes for returning
    return_notes = models.TextField(blank=True, default='')
    
    # Condition of item upon return (only set by owner/admin, not borrower)
    condition = models.CharField(max_length=200, blank=True, default='')
    
    # Stored status (active or returned)
    status = models.CharField(
        max_length=20,
        choices=BorrowStatus.choices,
        default=BorrowStatus.ACTIVE
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'operations_borrowrecord'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item', 'status']),
            models.Index(fields=['borrower', '-created_at']),
            models.Index(fields=['operator', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['expected_return_date']),
        ]
        # Note: Partial unique index (uq_borrow_active_item) is created via migration
        # using RunSQL for: UNIQUE (item_id) WHERE status='active'
    
    def __str__(self):
        return f"Borrow: {self.item.sku} by {self.borrower.username} ({self.computed_status})"
    
    @property
    def computed_status(self) -> str:
        """
        Compute the display status based on current state.
        
        Uses timezone.localdate() instead of date.today() to ensure
        correct behavior when USE_TZ=True.
        
        Returns:
            BorrowComputedStatus value:
            - 'returned' if actual_return_datetime is not null
            - 'overdue' if status='active' AND today > expected_return_date
            - 'active' otherwise
        """
        if self.actual_return_datetime is not None:
            return BorrowComputedStatus.RETURNED
        
        if self.status == BorrowStatus.ACTIVE:
            today = timezone.localdate()
            if today > self.expected_return_date:
                return BorrowComputedStatus.OVERDUE
        
        return BorrowComputedStatus.ACTIVE
    
    @property
    def is_active(self) -> bool:
        """Check if the borrow is currently active."""
        return self.status == BorrowStatus.ACTIVE
    
    @property
    def is_returned(self) -> bool:
        """Check if the item has been returned."""
        return self.status == BorrowStatus.RETURNED
    
    @property
    def is_overdue(self) -> bool:
        """Check if the borrow is overdue."""
        return self.computed_status == BorrowComputedStatus.OVERDUE


class TakeRecord(models.Model):
    """
    Take record model for tracking consumable item taking.
    
    Records the taking of consumable items with quantity tracking.
    Each take operation decrements the item's quantity.
    
    Constraints:
    - Taker must be a system user
    - Quantity must be positive
    - Cannot take more than available quantity
    
    Requirements: 9.6
    """
    
    # The item being taken from
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        related_name='take_records'
    )
    
    # The user who took the item
    taker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='taken_records'
    )
    
    # The user who registered the take operation
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operated_take_records'
    )
    
    # Quantity taken
    quantity = models.PositiveIntegerField()
    
    # Notes for the take operation
    notes = models.TextField(blank=True, default='')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'operations_takerecord'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item', '-created_at']),
            models.Index(fields=['taker', '-created_at']),
            models.Index(fields=['operator', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Take: {self.quantity} x {self.item.sku} by {self.taker.username}"


class ReplenishRecord(models.Model):
    """
    Replenish record model for tracking consumable item replenishment.
    
    Records the replenishment of consumable items with quantity tracking.
    Each replenish operation increments the item's quantity.
    
    Requirements: 9.12
    """
    
    # The item being replenished
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.PROTECT,
        related_name='replenish_records'
    )
    
    # The user who registered the replenish operation
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operated_replenish_records'
    )
    
    # Quantity replenished
    quantity = models.PositiveIntegerField()
    
    # Notes for the replenish operation
    notes = models.TextField(blank=True, default='')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'operations_replenishrecord'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item', '-created_at']),
            models.Index(fields=['operator', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Replenish: {self.quantity} x {self.item.sku} by {self.operator.username}"
