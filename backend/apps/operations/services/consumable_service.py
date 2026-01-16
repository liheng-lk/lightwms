"""
Consumable service for LightWMS.

Handles take and replenish operations for consumable items with:
- Transaction safety (atomic operations)
- Proper locking (select_for_update)
- Quantity validation
- Status updates
- Audit logging
"""
from datetime import date
from typing import Optional, List

from django.db import transaction
from django.db.models import QuerySet

from apps.inventory.models import Item, ItemType, ItemStatus
from apps.operations.models import TakeRecord, ReplenishRecord
from apps.audit.models import AuditLog, AuditAction, TargetType
from apps.users.models import User
from core.exceptions import BusinessConflictError


class ConsumableService:
    """
    Service class for take/replenish operations on consumable items.
    
    All operations use database transactions with select_for_update
    to ensure consistency under concurrent access.
    
    Requirements: 9.1-9.14
    """
    
    @classmethod
    def _get_item_audit_data(cls, item: Item) -> dict:
        """Extract audit-safe data from item."""
        return {
            'status': item.status,
            'quantity': item.quantity,
            'is_active': item.is_active,
        }
    
    @classmethod
    def _get_take_audit_data(cls, record: TakeRecord) -> dict:
        """Extract audit-safe data from take record."""
        return {
            'item_id': record.item_id,
            'taker_id': record.taker_id,
            'operator_id': record.operator_id,
            'quantity': record.quantity,
            'notes': record.notes,
        }
    
    @classmethod
    def _get_replenish_audit_data(cls, record: ReplenishRecord) -> dict:
        """Extract audit-safe data from replenish record."""
        return {
            'item_id': record.item_id,
            'operator_id': record.operator_id,
            'quantity': record.quantity,
            'notes': record.notes,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        target_type: str,
        target_id: int,
        before: Optional[dict],
        after: Optional[dict],
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry."""
        return AuditLog.objects.create(
            action=action,
            target_type=target_type,
            target_id=target_id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    def _validate_item_for_take(cls, item: Item) -> None:
        """
        Validate that an item can be taken from.
        
        Raises:
            BusinessConflictError: If item cannot be taken from
        """
        # Check item is active
        if not item.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot take from inactive item.',
                details={'item_id': item.id}
            )
        
        # Check item is consumable
        if item.type != ItemType.CONSUMABLE:
            raise BusinessConflictError(
                code='INVALID_ITEM_TYPE',
                message='Only consumable items can be taken.',
                details={'item_id': item.id, 'type': item.type}
            )
    
    @classmethod
    def _validate_item_for_replenish(cls, item: Item) -> None:
        """
        Validate that an item can be replenished.
        
        Raises:
            BusinessConflictError: If item cannot be replenished
        """
        # Check item is active
        if not item.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot replenish inactive item.',
                details={'item_id': item.id}
            )
        
        # Check item is consumable
        if item.type != ItemType.CONSUMABLE:
            raise BusinessConflictError(
                code='INVALID_ITEM_TYPE',
                message='Only consumable items can be replenished.',
                details={'item_id': item.id, 'type': item.type}
            )
    
    @classmethod
    def _validate_taker(cls, taker_id: int) -> User:
        """
        Validate that taker is a system user.
        
        Args:
            taker_id: ID of the taker
            
        Returns:
            User instance
            
        Raises:
            BusinessConflictError: If taker not found or inactive
        """
        try:
            taker = User.objects.get(id=taker_id)
        except User.DoesNotExist:
            raise BusinessConflictError(
                code='INVALID_TAKER',
                message='Taker must be a system user.',
                details={'taker_id': taker_id}
            )
        
        if not taker.is_active:
            raise BusinessConflictError(
                code='TAKER_INACTIVE',
                message='Taker account is inactive.',
                details={'taker_id': taker_id}
            )
        
        return taker
    
    @classmethod
    @transaction.atomic
    def take(
        cls,
        item_id: int,
        taker_id: int,
        quantity: int,
        notes: str,
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> TakeRecord:
        """
        Register a take operation for a consumable item.
        
        This method:
        1. Locks the item with select_for_update
        2. Validates item can be taken from (consumable, active)
        3. Validates taker is a system user
        4. Validates quantity <= item.quantity
        5. Decrements item.quantity
        6. Updates item.status to 'out_of_stock' if quantity becomes 0
        7. Creates TakeRecord
        8. Creates audit log
        
        Args:
            item_id: ID of item to take from
            taker_id: ID of user taking the item
            quantity: Quantity to take
            notes: Notes for the take operation
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created TakeRecord
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If item cannot be taken from or insufficient quantity
            
        Requirements: 9.1-9.8
        """
        # Validate quantity is positive
        if quantity <= 0:
            raise BusinessConflictError(
                code='INVALID_QUANTITY',
                message='Quantity must be positive.',
                details={'quantity': quantity}
            )
        
        # Lock item with select_for_update
        item = Item.objects.select_for_update().get(id=item_id)
        
        # Validate item can be taken from
        cls._validate_item_for_take(item)
        
        # Validate taker
        cls._validate_taker(taker_id)
        
        # Validate quantity
        if item.quantity is None or quantity > item.quantity:
            raise BusinessConflictError(
                code='INSUFFICIENT_QUANTITY',
                message='Cannot take more than available quantity.',
                details={
                    'item_id': item.id,
                    'requested': quantity,
                    'available': item.quantity
                }
            )
        
        # Capture item state before change
        item_before = cls._get_item_audit_data(item)
        
        # Decrement quantity
        item.quantity -= quantity
        
        # Update status if quantity becomes 0
        if item.quantity == 0:
            item.status = ItemStatus.OUT_OF_STOCK
        
        item.save(update_fields=['quantity', 'status', 'updated_at'])
        
        # Create take record
        record = TakeRecord.objects.create(
            item_id=item_id,
            taker_id=taker_id,
            operator=operator,
            quantity=quantity,
            notes=notes,
        )
        
        # Create audit log for take action
        cls._create_audit_log(
            action=AuditAction.TAKE,
            target_type=TargetType.ITEM,
            target_id=item.id,
            before=item_before,
            after=cls._get_item_audit_data(item),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Create audit log for take record creation
        cls._create_audit_log(
            action=AuditAction.CREATE,
            target_type=TargetType.TAKE_RECORD,
            target_id=record.id,
            before=None,
            after=cls._get_take_audit_data(record),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return record
    
    @classmethod
    @transaction.atomic
    def replenish(
        cls,
        item_id: int,
        quantity: int,
        notes: str,
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> ReplenishRecord:
        """
        Register a replenish operation for a consumable item.
        
        This method:
        1. Locks the item with select_for_update
        2. Validates item can be replenished (consumable, active)
        3. Increments item.quantity
        4. Updates item.status to 'in_stock' if quantity becomes > 0
        5. Creates ReplenishRecord
        6. Creates audit log
        
        Args:
            item_id: ID of item to replenish
            quantity: Quantity to add
            notes: Notes for the replenish operation
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created ReplenishRecord
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If item cannot be replenished
            
        Requirements: 9.9-9.13
        """
        # Validate quantity is positive
        if quantity <= 0:
            raise BusinessConflictError(
                code='INVALID_QUANTITY',
                message='Quantity must be positive.',
                details={'quantity': quantity}
            )
        
        # Lock item with select_for_update
        item = Item.objects.select_for_update().get(id=item_id)
        
        # Validate item can be replenished
        cls._validate_item_for_replenish(item)
        
        # Capture item state before change
        item_before = cls._get_item_audit_data(item)
        
        # Increment quantity
        current_quantity = item.quantity if item.quantity is not None else 0
        item.quantity = current_quantity + quantity
        
        # Update status to in_stock
        item.status = ItemStatus.IN_STOCK
        
        item.save(update_fields=['quantity', 'status', 'updated_at'])
        
        # Create replenish record
        record = ReplenishRecord.objects.create(
            item_id=item_id,
            operator=operator,
            quantity=quantity,
            notes=notes,
        )
        
        # Create audit log for replenish action
        cls._create_audit_log(
            action=AuditAction.REPLENISH,
            target_type=TargetType.ITEM,
            target_id=item.id,
            before=item_before,
            after=cls._get_item_audit_data(item),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Create audit log for replenish record creation
        cls._create_audit_log(
            action=AuditAction.CREATE,
            target_type=TargetType.REPLENISH_RECORD,
            target_id=record.id,
            before=None,
            after=cls._get_replenish_audit_data(record),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return record
    
    @classmethod
    def list_take_records(
        cls,
        item_id: Optional[int] = None,
        taker_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        visible_taker_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QuerySet:
        """
        List take records with optional filters.
        
        Args:
            item_id: Filter by item ID
            taker_id: Filter by taker ID
            owner_id: Filter by item owner ID (for data isolation)
            visible_taker_id: Also include records where taker_id matches (for data isolation)
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            
        Returns:
            QuerySet of TakeRecord
            
        Requirements: 10.5
        """
        from django.db.models import Q
        
        qs = TakeRecord.objects.select_related(
            'item', 'item__owner', 'taker', 'operator'
        )
        
        if item_id:
            qs = qs.filter(item_id=item_id)
        
        if taker_id:
            qs = qs.filter(taker_id=taker_id)
        
        # Data isolation: owner_id OR visible_taker_id
        if owner_id and visible_taker_id:
            qs = qs.filter(Q(item__owner_id=owner_id) | Q(taker_id=visible_taker_id))
        elif owner_id:
            qs = qs.filter(item__owner_id=owner_id)
        elif visible_taker_id:
            qs = qs.filter(taker_id=visible_taker_id)
        
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        
        return qs.order_by('-created_at')
    
    @classmethod
    def list_replenish_records(
        cls,
        item_id: Optional[int] = None,
        operator_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        visible_operator_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QuerySet:
        """
        List replenish records with optional filters.
        
        Args:
            item_id: Filter by item ID
            operator_id: Filter by operator ID
            owner_id: Filter by item owner ID (for data isolation)
            visible_operator_id: Also include records where operator_id matches (for data isolation)
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            
        Returns:
            QuerySet of ReplenishRecord
            
        Requirements: 10.6
        """
        from django.db.models import Q
        
        qs = ReplenishRecord.objects.select_related(
            'item', 'item__owner', 'operator'
        )
        
        if item_id:
            qs = qs.filter(item_id=item_id)
        
        if operator_id:
            qs = qs.filter(operator_id=operator_id)
        
        # Data isolation: owner_id OR visible_operator_id
        if owner_id and visible_operator_id:
            qs = qs.filter(Q(item__owner_id=owner_id) | Q(operator_id=visible_operator_id))
        elif owner_id:
            qs = qs.filter(item__owner_id=owner_id)
        elif visible_operator_id:
            qs = qs.filter(operator_id=visible_operator_id)
        
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        
        return qs.order_by('-created_at')
