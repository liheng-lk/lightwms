"""
Item service for LightWMS.

Handles item CRUD operations with audit logging.
"""
import base64
import io
import random
import string
from dataclasses import dataclass
from typing import Optional

from django.db import transaction, IntegrityError

from apps.inventory.models import Item, ItemType, ItemStatus, Location, Category, Warehouse
from apps.audit.models import AuditLog, AuditAction, TargetType
from core.exceptions import BusinessConflictError


@dataclass
class ItemCreateDTO:
    """Data transfer object for item creation."""
    name: str
    sku: str
    location_id: int
    type: str = ItemType.REUSABLE
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    unit: str = ''
    description: str = ''
    owner_id: Optional[int] = None
    quantity: Optional[int] = None


@dataclass
class ItemUpdateDTO:
    """Data transfer object for item update."""
    name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    quantity: Optional[int] = None


@dataclass
class BarcodeLabelResult:
    """Result of barcode generation."""
    barcode: str
    label_png_base64: str


class ItemService:
    """
    Service class for item operations.
    
    All operations that modify data create audit log entries.
    Items use soft delete (is_active=False) instead of hard delete.
    
    Status is managed by the service layer:
    - Reusable items: available (default), borrowed (set by BorrowService)
    - Consumable items: in_stock (quantity > 0), out_of_stock (quantity = 0)
    """
    
    # Fields to exclude from audit diff
    AUDIT_EXCLUDE_FIELDS = {'id', 'created_at', 'updated_at', 'search_vector'}
    
    # Barcode generation settings
    BARCODE_PREFIX = 'BC'
    BARCODE_LENGTH = 12  # Total length including prefix
    BARCODE_MAX_RETRIES = 5
    
    @classmethod
    def _get_audit_data(cls, item: Item) -> dict:
        """Extract audit-safe data from item."""
        return {
            'name': item.name,
            'sku': item.sku,
            'barcode': item.barcode,
            'category_id': item.category_id,
            'unit': item.unit,
            'description': item.description,
            'location_id': item.location_id,
            'owner_id': item.owner_id,
            'type': item.type,
            'status': item.status,
            'quantity': item.quantity,
            'is_active': item.is_active,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        item: Item,
        before: Optional[dict],
        after: Optional[dict],
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry for item operations."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.ITEM,
            target_id=item.id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    def _validate_location(cls, location_id: int) -> Location:
        """
        Validate location exists and its warehouse is active.
        
        Raises:
            Location.DoesNotExist: If location not found
            BusinessConflictError: If warehouse is inactive
        """
        location = Location.objects.select_related('warehouse').get(id=location_id)
        
        if not location.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot use inactive location.',
                details={'location_id': location_id}
            )
        
        if not location.warehouse.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot create item in inactive warehouse.',
                details={'warehouse_id': location.warehouse_id}
            )
        
        return location
    
    @classmethod
    def _validate_category(cls, category_id: int) -> Category:
        """
        Validate category exists and is active.
        
        Raises:
            Category.DoesNotExist: If category not found
            BusinessConflictError: If category is inactive
        """
        category = Category.objects.get(id=category_id)
        
        if not category.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot use inactive category.',
                details={'category_id': category_id}
            )
        
        return category
    
    @classmethod
    def _determine_initial_status(cls, item_type: str, quantity: Optional[int]) -> str:
        """
        Determine initial status based on item type and quantity.
        
        Args:
            item_type: 'reusable' or 'consumable'
            quantity: Quantity for consumable items
            
        Returns:
            Initial status string
        """
        if item_type == ItemType.REUSABLE:
            return ItemStatus.AVAILABLE
        else:  # consumable
            if quantity is not None and quantity > 0:
                return ItemStatus.IN_STOCK
            return ItemStatus.OUT_OF_STOCK
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        data: ItemCreateDTO,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Item:
        """
        Create a new item.
        
        Args:
            data: ItemCreateDTO with item data
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Item instance
            
        Raises:
            Location.DoesNotExist: If location not found
            Category.DoesNotExist: If category not found
            BusinessConflictError: If location/category/warehouse is inactive
            IntegrityError: If SKU or barcode already exists
        """
        # Validate location
        cls._validate_location(data.location_id)
        
        # Validate category if provided
        if data.category_id:
            cls._validate_category(data.category_id)
        
        # Determine owner (default to operator if not specified)
        owner_id = data.owner_id if data.owner_id else operator.id
        
        # Determine initial status
        status = cls._determine_initial_status(data.type, data.quantity)
        
        # Set quantity based on item type
        if data.type == ItemType.CONSUMABLE:
            quantity = data.quantity if data.quantity is not None else 0
        else:  # REUSABLE
            quantity = data.quantity if data.quantity is not None else 1
            if quantity < 1:
                quantity = 1
        
        try:
            item = Item.objects.create(
                name=data.name,
                sku=data.sku,
                barcode=data.barcode if data.barcode else None,
                category_id=data.category_id,
                unit=data.unit,
                description=data.description,
                location_id=data.location_id,
                owner_id=owner_id,
                type=data.type,
                status=status,
                quantity=quantity,
                is_active=True,
            )
        except IntegrityError as e:
            # Re-raise with semantic error if we can identify the constraint
            cls._handle_integrity_error(e)
            raise
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.CREATE,
            item=item,
            before=None,
            after=cls._get_audit_data(item),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return item
    
    @classmethod
    def _handle_integrity_error(cls, exc: IntegrityError):
        """
        Handle IntegrityError by mapping to semantic BusinessConflictError.
        
        Raises:
            BusinessConflictError: If constraint can be identified
        """
        constraint_name = None
        if hasattr(exc, '__cause__') and exc.__cause__:
            cause = exc.__cause__
            if hasattr(cause, 'diag') and hasattr(cause.diag, 'constraint_name'):
                constraint_name = cause.diag.constraint_name
        
        if constraint_name == 'uq_item_sku':
            raise BusinessConflictError(
                code='DUPLICATE_SKU',
                message='An item with this SKU already exists.',
                details={'constraint': constraint_name}
            )
        elif constraint_name == 'uq_item_barcode_not_null':
            raise BusinessConflictError(
                code='DUPLICATE_BARCODE',
                message='An item with this barcode already exists.',
                details={'constraint': constraint_name}
            )
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        item_id: int,
        data: ItemUpdateDTO,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Item:
        """
        Update an item.
        
        Args:
            item_id: ID of item to update
            data: ItemUpdateDTO with fields to update
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated Item instance
            
        Raises:
            Item.DoesNotExist: If item not found
            Location.DoesNotExist: If new location not found
            Category.DoesNotExist: If new category not found
            BusinessConflictError: If location/category is inactive or barcode duplicate
        """
        item = Item.objects.select_for_update().get(id=item_id)
        before = cls._get_audit_data(item)
        
        # Validate new location if provided
        if data.location_id is not None:
            cls._validate_location(data.location_id)
            item.location_id = data.location_id
        
        # Validate new category if provided
        if data.category_id is not None:
            if data.category_id:
                cls._validate_category(data.category_id)
            item.category_id = data.category_id
        
        # Update other fields
        if data.name is not None:
            item.name = data.name
        if data.barcode is not None:
            item.barcode = data.barcode if data.barcode else None
        if data.unit is not None:
            item.unit = data.unit
        if data.description is not None:
            item.description = data.description
        
        # Update quantity for reusable items
        if data.quantity is not None and item.type == ItemType.REUSABLE:
            if data.quantity < 1:
                raise BusinessConflictError(
                    code='INVALID_QUANTITY',
                    message='Quantity for reusable items must be at least 1.',
                    details={'quantity': data.quantity}
                )
            # Check if new quantity is less than currently borrowed
            borrowed = item.borrowed_quantity
            if data.quantity < borrowed:
                raise BusinessConflictError(
                    code='QUANTITY_LESS_THAN_BORROWED',
                    message=f'Cannot set quantity to {data.quantity}. Currently {borrowed} items are borrowed.',
                    details={'quantity': data.quantity, 'borrowed': borrowed}
                )
            item.quantity = data.quantity
            # Re-derive status inside the same locked transaction; doing it
            # afterwards in the view raced with concurrent borrows.
            item.status = (
                ItemStatus.BORROWED
                if data.quantity - borrowed == 0
                else ItemStatus.AVAILABLE
            )
        
        try:
            item.save()
        except IntegrityError as e:
            cls._handle_integrity_error(e)
            raise
        
        after = cls._get_audit_data(item)
        
        # Only create audit log if something changed
        if before != after:
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                item=item,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
        
        return item
    
    @classmethod
    @transaction.atomic
    def deactivate(
        cls,
        item_id: int,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Item:
        """
        Deactivate an item (soft delete).
        
        When an item is deactivated:
        - It cannot be borrowed, taken, or replenished
        - Associated records are preserved
        - It is excluded from default queries
        
        Args:
            item_id: ID of item to deactivate
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Deactivated Item instance
            
        Raises:
            Item.DoesNotExist: If item not found
        """
        item = Item.objects.select_for_update().get(id=item_id)
        
        if not item.is_active:
            # Already deactivated, no-op
            return item
        
        before = cls._get_audit_data(item)
        
        item.is_active = False
        item.save(update_fields=['is_active', 'updated_at'])
        
        after = cls._get_audit_data(item)
        
        cls._create_audit_log(
            action=AuditAction.DEACTIVATE,
            item=item,
            before=before,
            after=after,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return item
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        item_id: int,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> None:
        """
        Permanently delete an item (hard delete).
        
        WARNING: This permanently removes the item and all associated data.
        Use deactivate() for soft delete if you want to preserve data.
        
        Cannot delete if:
        - Item has borrow records
        - Item has take records
        - Item has replenish records
        
        Args:
            item_id: ID of item to delete
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If item has related records
        """
        item = Item.objects.select_for_update().get(id=item_id)
        
        # Check for related records that would prevent deletion
        # Import here to avoid circular imports
        from apps.operations.models import BorrowRecord, TakeRecord, ReplenishRecord
        
        borrow_count = BorrowRecord.objects.filter(item_id=item_id).count()
        if borrow_count > 0:
            raise BusinessConflictError(
                code='ITEM_HAS_BORROW_RECORDS',
                message='Cannot delete item with borrow records.',
                details={'borrow_count': borrow_count}
            )
        
        take_count = TakeRecord.objects.filter(item_id=item_id).count()
        if take_count > 0:
            raise BusinessConflictError(
                code='ITEM_HAS_TAKE_RECORDS',
                message='Cannot delete item with take records.',
                details={'take_count': take_count}
            )
        
        replenish_count = ReplenishRecord.objects.filter(item_id=item_id).count()
        if replenish_count > 0:
            raise BusinessConflictError(
                code='ITEM_HAS_REPLENISH_RECORDS',
                message='Cannot delete item with replenish records.',
                details={'replenish_count': replenish_count}
            )
        
        before = cls._get_audit_data(item)
        
        # Create audit log before deletion
        AuditLog.objects.create(
            action=AuditAction.DELETE,
            target_type=TargetType.ITEM,
            target_id=item_id,
            diff={'before': before, 'after': None},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
        
        # Delete the item (this will cascade delete related images)
        item.delete()
    
    @classmethod
    def _generate_barcode_string(cls) -> str:
        """Generate a random barcode string."""
        suffix_length = cls.BARCODE_LENGTH - len(cls.BARCODE_PREFIX)
        suffix = ''.join(random.choices(string.digits, k=suffix_length))
        return f"{cls.BARCODE_PREFIX}{suffix}"
    
    @classmethod
    def _generate_barcode_label(cls, barcode: str) -> str:
        """
        Generate a barcode label image as base64 PNG.
        
        Args:
            barcode: Barcode string
            
        Returns:
            Base64-encoded PNG image
        """
        try:
            from barcode import Code128
            from barcode.writer import ImageWriter
            
            # Generate Code128 barcode
            bc = Code128(barcode, writer=ImageWriter())
            
            # Write to bytes buffer
            buffer = io.BytesIO()
            bc.write(buffer)
            buffer.seek(0)
            
            return base64.b64encode(buffer.read()).decode('utf-8')
        except ImportError:
            # Fallback if barcode library not installed
            # Return a placeholder base64 string
            placeholder = f"BARCODE:{barcode}".encode('utf-8')
            return base64.b64encode(placeholder).decode('utf-8')
    
    @classmethod
    @transaction.atomic
    def generate_barcode(
        cls,
        item_id: int,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> BarcodeLabelResult:
        """
        Generate a unique barcode for an item, or return existing barcode.
        
        If the item already has a barcode, returns the existing barcode
        with a freshly generated label image. Otherwise, generates a new
        barcode with retry on conflict.
        
        Args:
            item_id: ID of item
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            BarcodeLabelResult with barcode string and PNG label
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If unable to generate unique barcode after retries
        """
        item = Item.objects.select_for_update().get(id=item_id)
        
        # If item already has a barcode, return it with a fresh label image
        if item.barcode:
            label_base64 = cls._generate_barcode_label(item.barcode)
            return BarcodeLabelResult(
                barcode=item.barcode,
                label_png_base64=label_base64
            )
        
        before = cls._get_audit_data(item)
        
        # Try to generate unique barcode with retries
        for attempt in range(cls.BARCODE_MAX_RETRIES):
            barcode = cls._generate_barcode_string()
            
            # Check if barcode already exists
            if not Item.objects.filter(barcode=barcode).exclude(id=item_id).exists():
                item.barcode = barcode
                try:
                    item.save(update_fields=['barcode', 'updated_at'])
                    break
                except IntegrityError:
                    # Race condition - another item got this barcode
                    continue
        else:
            raise BusinessConflictError(
                code='BARCODE_GENERATION_FAILED',
                message='Unable to generate unique barcode after multiple attempts.',
                details={'attempts': cls.BARCODE_MAX_RETRIES}
            )
        
        after = cls._get_audit_data(item)
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.UPDATE,
            item=item,
            before=before,
            after=after,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Generate label
        label_base64 = cls._generate_barcode_label(barcode)
        
        return BarcodeLabelResult(
            barcode=barcode,
            label_png_base64=label_base64
        )
    
    @classmethod
    def get_by_id(cls, item_id: int) -> Item:
        """
        Get an item by ID.
        
        Args:
            item_id: ID of item
            
        Returns:
            Item instance
            
        Raises:
            Item.DoesNotExist: If not found
        """
        return Item.objects.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        ).get(id=item_id)
    
    @classmethod
    def get_by_sku(cls, sku: str) -> Item:
        """
        Get an item by SKU.
        
        Args:
            sku: Item SKU
            
        Returns:
            Item instance
            
        Raises:
            Item.DoesNotExist: If not found
        """
        return Item.objects.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        ).get(sku=sku)
    
    @classmethod
    def list_active(cls, owner_id: Optional[int] = None):
        """
        Get all active items, optionally filtered by owner.
        
        Args:
            owner_id: Optional owner ID to filter by
            
        Returns:
            QuerySet of active items
        """
        qs = Item.objects.filter(is_active=True).select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        return qs.order_by('-updated_at', '-id')
    
    @classmethod
    def list_all(cls, owner_id: Optional[int] = None):
        """
        Get all items including inactive, optionally filtered by owner.
        
        Args:
            owner_id: Optional owner ID to filter by
            
        Returns:
            QuerySet of all items
        """
        qs = Item.objects.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        return qs.order_by('-updated_at', '-id')
    
    @classmethod
    @transaction.atomic
    def batch_update_location(
        cls,
        item_ids: list[int],
        location_id: int,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> int:
        """
        Batch update location for multiple items.
        
        Args:
            item_ids: List of item IDs to update
            location_id: Target location ID
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Number of items updated
            
        Raises:
            Location.DoesNotExist: If location not found
            BusinessConflictError: If location is inactive
        """
        if not item_ids:
            return 0
        
        # Validate location
        location = cls._validate_location(location_id)
        
        # Get items to update
        items = Item.objects.filter(id__in=item_ids, is_active=True).select_for_update()
        
        updated_count = 0
        for item in items:
            if item.location_id == location_id:
                continue  # Skip if already at target location
            
            before = cls._get_audit_data(item)
            item.location_id = location_id
            item.save(update_fields=['location_id', 'updated_at'])
            after = cls._get_audit_data(item)
            
            # Create audit log for each item
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                item=item,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
            updated_count += 1
        
        return updated_count
    
    @classmethod
    @transaction.atomic
    def batch_update_owner(
        cls,
        item_ids: list[int],
        owner_id: int,
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> int:
        """
        Batch update owner for multiple items.
        
        Args:
            item_ids: List of item IDs to update
            owner_id: Target owner (user) ID
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Number of items updated
            
        Raises:
            User.DoesNotExist: If user not found
            BusinessConflictError: If user is inactive
        """
        from apps.users.models import User
        
        if not item_ids:
            return 0
        
        # Validate owner
        try:
            owner = User.objects.get(id=owner_id)
        except User.DoesNotExist:
            raise BusinessConflictError(
                code='USER_NOT_FOUND',
                message='Target user not found.',
                details={'owner_id': owner_id}
            )
        
        if not owner.is_active:
            raise BusinessConflictError(
                code='USER_INACTIVE',
                message='Cannot assign items to inactive user.',
                details={'owner_id': owner_id}
            )
        
        # Get items to update
        items = Item.objects.filter(id__in=item_ids, is_active=True).select_for_update()
        
        updated_count = 0
        for item in items:
            if item.owner_id == owner_id:
                continue  # Skip if already owned by target user
            
            before = cls._get_audit_data(item)
            item.owner_id = owner_id
            item.save(update_fields=['owner_id', 'updated_at'])
            after = cls._get_audit_data(item)
            
            # Create audit log for each item
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                item=item,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
            updated_count += 1
        
        return updated_count
