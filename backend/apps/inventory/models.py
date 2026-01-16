"""
Inventory models for LightWMS.

This module contains models for:
- Warehouse: Top-level container for items
- Location: Hierarchical storage locations within warehouses
- Category: Hierarchical classification for items
- Item: Physical items in the warehouse
- ItemImage: Images associated with items
"""
from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField


class Warehouse(models.Model):
    """
    Warehouse model representing a physical warehouse.
    
    Warehouses are the top-level containers for organizing items.
    They contain locations which form a hierarchical structure.
    
    Soft delete is implemented via is_active=False.
    When deactivated:
    - New Locations cannot be created under this warehouse
    - New Items cannot be created under locations in this warehouse
    - Existing data is preserved but excluded from default queries
    """
    
    # Unique warehouse code (e.g., "WH-001")
    code = models.CharField(max_length=50, unique=True)
    
    # Human-readable name
    name = models.CharField(max_length=100)
    
    # Optional description
    description = models.TextField(blank=True, default='')
    
    # Soft delete flag
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_warehouse'
        ordering = ['code']
        indexes = [
            models.Index(fields=['is_active', 'code']),
            models.Index(fields=['-updated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                name='uq_warehouse_code'
            ),
        ]
    
    def __str__(self):
        status = '' if self.is_active else ' [Inactive]'
        return f"{self.code} - {self.name}{status}"


class Location(models.Model):
    """
    Location model representing a storage location within a warehouse.
    
    Locations form a hierarchical tree structure using adjacency list pattern.
    Each location belongs to exactly one warehouse and can have a parent location.
    
    Constraints:
    - Parent location must belong to the same warehouse
    - Code must be unique within a warehouse
    - Cannot be deactivated if it has active children or any items
    
    Soft delete is implemented via is_active=False.
    """
    
    # Parent warehouse (required)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='locations'
    )
    
    # Parent location (null for root locations)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Location code (unique within warehouse)
    code = models.CharField(max_length=50)
    
    # Human-readable name
    name = models.CharField(max_length=100)
    
    # Location owner/manager (required)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_locations'
    )
    
    # Soft delete flag
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_location'
        ordering = ['warehouse', 'code']
        indexes = [
            models.Index(fields=['warehouse', 'is_active', 'code']),
            models.Index(fields=['parent']),
            models.Index(fields=['-updated_at']),
        ]
        constraints = [
            # Unique code within warehouse
            models.UniqueConstraint(
                fields=['warehouse', 'code'],
                name='uq_location_warehouse_code'
            ),
        ]
    
    def __str__(self):
        status = '' if self.is_active else ' [Inactive]'
        return f"{self.warehouse.code}/{self.code} - {self.name}{status}"
    
    @property
    def full_path(self) -> str:
        """
        Get the full path from root to this location.
        
        Returns:
            String like "WH-001/A/A1/A1-01"
        """
        parts = [self.code]
        current = self.parent
        while current:
            parts.insert(0, current.code)
            current = current.parent
        parts.insert(0, self.warehouse.code)
        return '/'.join(parts)


class Category(models.Model):
    """
    Category model representing a hierarchical classification for items.
    
    Categories form a tree structure using adjacency list pattern.
    Each category can have a parent category and multiple children.
    
    Constraints:
    - Cannot be deactivated if it has child categories (active or inactive)
    - Cannot be deactivated if it has any items (active or inactive)
    
    Soft delete is implemented via is_active=False.
    """
    
    # Parent category (null for root categories)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Category name
    name = models.CharField(max_length=100)
    
    # Soft delete flag
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_category'
        verbose_name_plural = 'categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['parent']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        status = '' if self.is_active else ' [Inactive]'
        return f"{self.name}{status}"
    
    @property
    def full_path(self) -> str:
        """
        Get the full path from root to this category.
        
        Returns:
            String like "Electronics/Computers/Laptops"
        """
        parts = [self.name]
        current = self.parent
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return '/'.join(parts)


class ItemType(models.TextChoices):
    """Item type enumeration."""
    REUSABLE = 'reusable', 'Reusable'
    CONSUMABLE = 'consumable', 'Consumable'


class ItemStatus(models.TextChoices):
    """Item status enumeration."""
    # For reusable items
    AVAILABLE = 'available', 'Available'
    BORROWED = 'borrowed', 'Borrowed'
    # For consumable items
    IN_STOCK = 'in_stock', 'In Stock'
    OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'


class Item(models.Model):
    """
    Item model representing a physical item in the warehouse.
    
    Items can be either reusable (can be borrowed/returned) or
    consumable (can be taken/replenished with quantity tracking).
    
    Status values depend on item type:
    - Reusable: available, borrowed
    - Consumable: in_stock, out_of_stock
    
    Constraints:
    - SKU must be unique (uq_item_sku)
    - Barcode must be unique when not null (uq_item_barcode_not_null)
    - Status must be valid for the item type (chk_item_status_type)
    
    Soft delete is implemented via is_active=False.
    When deactivated:
    - Item cannot be borrowed, taken, or replenished
    - Associated records (BorrowRecord, TakeRecord, etc.) are preserved
    - Item is excluded from default queries
    """
    
    # Basic information
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    
    # Classification
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='items',
        null=True,
        blank=True
    )
    
    # Physical attributes
    unit = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True, default='')
    
    # Location
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='items'
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_items'
    )
    
    # Type and status
    type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.REUSABLE
    )
    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.AVAILABLE
    )
    
    # Quantity (for both reusable and consumable items)
    # For reusable: total quantity of identical items
    # For consumable: current stock quantity
    quantity = models.PositiveIntegerField(default=1)
    
    # Soft delete flag
    is_active = models.BooleanField(default=True)
    
    # Full-text search vector (updated by database trigger)
    search_vector = SearchVectorField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_item'
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['is_active', '-updated_at', '-id']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['location', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['sku']),
        ]
        constraints = [
            # Unique constraint on SKU
            models.UniqueConstraint(
                fields=['sku'],
                name='uq_item_sku'
            ),
            # Check constraint for status/type consistency
            models.CheckConstraint(
                check=(
                    models.Q(type='reusable', status__in=['available', 'borrowed']) |
                    models.Q(type='consumable', status__in=['in_stock', 'out_of_stock'])
                ),
                name='chk_item_status_type'
            ),
        ]
    
    def __str__(self):
        status = '' if self.is_active else ' [Inactive]'
        return f"{self.sku} - {self.name}{status}"
    
    @property
    def is_reusable(self) -> bool:
        """Check if item is reusable type."""
        return self.type == ItemType.REUSABLE
    
    @property
    def is_consumable(self) -> bool:
        """Check if item is consumable type."""
        return self.type == ItemType.CONSUMABLE
    
    @property
    def borrowed_quantity(self) -> int:
        """Get the quantity currently borrowed (for reusable items)."""
        if not self.is_reusable:
            return 0
        from apps.operations.models import BorrowRecord, BorrowStatus
        return BorrowRecord.objects.filter(
            item_id=self.id,
            status=BorrowStatus.ACTIVE
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def available_quantity(self) -> int:
        """Get the available quantity for borrowing/taking."""
        if self.is_reusable:
            return self.quantity - self.borrowed_quantity
        else:
            return self.quantity
    
    @property
    def is_available(self) -> bool:
        """Check if reusable item has available quantity for borrowing."""
        return self.is_reusable and self.available_quantity > 0
    
    @property
    def is_borrowed(self) -> bool:
        """Check if reusable item is currently borrowed (any quantity)."""
        return self.is_reusable and self.borrowed_quantity > 0
    
    @property
    def is_fully_borrowed(self) -> bool:
        """Check if all quantity of reusable item is borrowed."""
        return self.is_reusable and self.available_quantity == 0
    
    @property
    def is_in_stock(self) -> bool:
        """Check if consumable item has stock."""
        return self.is_consumable and self.quantity > 0
    
    @property
    def is_out_of_stock(self) -> bool:
        """Check if consumable item is out of stock."""
        return self.is_consumable and self.quantity == 0


class ItemImage(models.Model):
    """
    Item image model for storing item photos.
    
    Each image is stored in multiple sizes:
    - original: Original image converted to WebP (max 2000px)
    - thumb_256: 256px thumbnail
    - thumb_768: 768px thumbnail
    - thumb_1600: 1600px thumbnail
    
    Constraints:
    - Only one image per item can be primary (uq_itemimage_primary)
    
    Storage path: /media/items/{item_id}/{image_id}/
    """
    
    # Parent item
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='images'
    )
    
    # Image paths
    original = models.CharField(max_length=500)
    thumb_256 = models.CharField(max_length=500)
    thumb_768 = models.CharField(max_length=500)
    thumb_1600 = models.CharField(max_length=500)
    
    # Primary image flag
    is_primary = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_itemimage'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item', 'is_primary']),
            models.Index(fields=['item', '-created_at']),
        ]
        constraints = [
            # Only one primary image per item (partial unique constraint)
            # This is created via migration with RunSQL for partial unique
        ]
    
    def __str__(self):
        primary = ' [Primary]' if self.is_primary else ''
        return f"Image for {self.item.sku}{primary}"
