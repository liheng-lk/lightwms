"""
Borrow service for LightWMS.

Handles borrow and return operations for reusable items with:
- Transaction safety (atomic operations)
- Proper locking (select_for_update)
- Audit logging
- Concurrent access protection
"""
from datetime import date
from typing import Optional, List

from django.db import transaction, IntegrityError
from django.db.models import QuerySet
from django.utils import timezone

from apps.inventory.models import Item, ItemType, ItemStatus
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.audit.models import AuditLog, AuditAction, TargetType
from apps.users.models import User
from core.exceptions import BusinessConflictError


class BorrowService:
    """
    Service class for borrow/return operations.
    
    All operations use database transactions with select_for_update
    to ensure consistency under concurrent access.
    
    Lock ordering (to prevent deadlocks):
    1. Item (always locked first)
    2. BorrowRecord (locked second, if needed)
    
    The _lock_item_then_record() helper enforces this ordering.
    """
    
    @classmethod
    def _get_item_audit_data(cls, item: Item) -> dict:
        """Extract audit-safe data from item."""
        return {
            'status': item.status,
            'is_active': item.is_active,
        }
    
    @classmethod
    def _get_borrow_audit_data(cls, record: BorrowRecord) -> dict:
        """Extract audit-safe data from borrow record."""
        return {
            'item_id': record.item_id,
            'borrower_id': record.borrower_id,
            'operator_id': record.operator_id,
            'quantity': record.quantity,
            'expected_return_date': str(record.expected_return_date),
            'actual_return_datetime': str(record.actual_return_datetime) if record.actual_return_datetime else None,
            'notes': record.notes,
            'return_notes': record.return_notes,
            'condition': record.condition,
            'status': record.status,
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
    def _lock_item_then_record(
        cls,
        item_id: int,
        lock_record: bool = False
    ) -> tuple:
        """
        Lock item and optionally its active borrow record in correct order.
        
        This helper enforces the lock ordering invariant:
        1. Item is always locked first
        2. BorrowRecord is locked second (if requested)
        
        This prevents deadlocks when concurrent operations occur.
        
        Args:
            item_id: ID of the item to lock
            lock_record: Whether to also lock the active borrow record
            
        Returns:
            Tuple of (Item, BorrowRecord or None)
            
        Raises:
            Item.DoesNotExist: If item not found
        """
        # Lock item first (always)
        item = Item.objects.select_for_update().get(id=item_id)
        
        # Lock active borrow record second (if requested)
        record = None
        if lock_record:
            record = BorrowRecord.objects.select_for_update().filter(
                item_id=item_id,
                status=BorrowStatus.ACTIVE
            ).first()
        
        return item, record
    
    @classmethod
    def _validate_item_for_borrow(cls, item: Item, quantity: int = 1) -> None:
        """
        Validate that an item can be borrowed.
        
        Args:
            item: Item to validate
            quantity: Quantity to borrow
        
        Raises:
            BusinessConflictError: If item cannot be borrowed
        """
        # Check item is active
        if not item.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot borrow inactive item.',
                details={'item_id': item.id}
            )
        
        # Check item is reusable
        if item.type != ItemType.REUSABLE:
            raise BusinessConflictError(
                code='INVALID_ITEM_TYPE',
                message='Only reusable items can be borrowed.',
                details={'item_id': item.id, 'type': item.type}
            )
        
        # Check quantity is valid
        if quantity < 1:
            raise BusinessConflictError(
                code='INVALID_QUANTITY',
                message='Quantity must be at least 1.',
                details={'quantity': quantity}
            )
        
        # Check available quantity
        available = item.available_quantity
        if available < quantity:
            raise BusinessConflictError(
                code='INSUFFICIENT_QUANTITY',
                message=f'Not enough available quantity. Available: {available}, Requested: {quantity}',
                details={'item_id': item.id, 'available': available, 'requested': quantity}
            )
    
    @classmethod
    def _validate_borrower(cls, borrower_id: int) -> User:
        """
        Validate that borrower is a system user.
        
        Args:
            borrower_id: ID of the borrower
            
        Returns:
            User instance
            
        Raises:
            BusinessConflictError: If borrower not found or inactive
        """
        try:
            borrower = User.objects.get(id=borrower_id)
        except User.DoesNotExist:
            raise BusinessConflictError(
                code='INVALID_BORROWER',
                message='Borrower must be a system user.',
                details={'borrower_id': borrower_id}
            )
        
        if not borrower.is_active:
            raise BusinessConflictError(
                code='BORROWER_INACTIVE',
                message='Borrower account is inactive.',
                details={'borrower_id': borrower_id}
            )
        
        return borrower
    
    @classmethod
    @transaction.atomic
    def borrow(
        cls,
        item_id: int,
        borrower_id: int,
        expected_return_date: date,
        notes: str,
        operator: User,
        quantity: int = 1,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> BorrowRecord:
        """
        Register a borrow operation for a reusable item.
        
        This method:
        1. Locks the item with select_for_update
        2. Validates item can be borrowed (reusable, available quantity, active)
        3. Validates borrower is a system user
        4. Creates BorrowRecord with status='active' and quantity
        5. Updates Item.status to 'borrowed' if all quantity is borrowed
        6. Creates audit log
        
        Concurrent borrow attempts are serialized by the database lock.
        
        Args:
            item_id: ID of item to borrow
            borrower_id: ID of user borrowing the item
            expected_return_date: Expected return date
            notes: Notes for the borrow
            operator: User performing the operation
            quantity: Number of items to borrow (default 1)
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created BorrowRecord
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If item cannot be borrowed
        """
        # Lock item (no need to lock record for borrow)
        item, _ = cls._lock_item_then_record(item_id, lock_record=False)
        
        # Validate item can be borrowed with requested quantity
        cls._validate_item_for_borrow(item, quantity)
        
        # Validate borrower
        cls._validate_borrower(borrower_id)
        
        # Capture item state before change
        item_before = cls._get_item_audit_data(item)
        
        try:
            # Create borrow record with quantity
            record = BorrowRecord.objects.create(
                item_id=item_id,
                borrower_id=borrower_id,
                operator=operator,
                expected_return_date=expected_return_date,
                notes=notes,
                quantity=quantity,
                status=BorrowStatus.ACTIVE,
            )
        except IntegrityError as e:
            # Handle race condition - another borrow succeeded first
            cls._handle_integrity_error(e)
            raise
        
        # Update item status if all quantity is now borrowed
        # Refresh to get accurate borrowed_quantity after creating record
        item.refresh_from_db()
        if item.available_quantity == 0:
            item.status = ItemStatus.BORROWED
            item.save(update_fields=['status', 'updated_at'])
        
        # Create audit log for borrow action
        cls._create_audit_log(
            action=AuditAction.BORROW,
            target_type=TargetType.ITEM,
            target_id=item.id,
            before=item_before,
            after=cls._get_item_audit_data(item),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Create audit log for borrow record creation
        cls._create_audit_log(
            action=AuditAction.CREATE,
            target_type=TargetType.BORROW_RECORD,
            target_id=record.id,
            before=None,
            after=cls._get_borrow_audit_data(record),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return record
    
    @classmethod
    def _handle_integrity_error(cls, exc: IntegrityError) -> None:
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
        
        if constraint_name == 'uq_borrow_active_item':
            raise BusinessConflictError(
                code='ITEM_ALREADY_BORROWED',
                message='This item is already borrowed.',
                details={'constraint': constraint_name}
            )
        
        # Re-raise as generic conflict for unknown constraints
        raise BusinessConflictError(
            code='CONCURRENT_CONFLICT',
            message='Concurrent modification conflict.',
            details={'constraint': constraint_name}
        )
    
    @classmethod
    @transaction.atomic
    def return_item(
        cls,
        item_id: int,
        return_notes: str,
        condition: str,
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> BorrowRecord:
        """
        Register a return operation for a borrowed item.
        
        This method:
        1. Locks item first, then borrow record (lock ordering)
        2. Validates there is an active borrow
        3. Validates operator is owner, admin, or current borrower
        4. If operator is borrower, ignores condition parameter
        5. Updates BorrowRecord with return info
        6. Updates Item.status to 'available'
        7. Creates audit log with operator_role
        
        Args:
            item_id: ID of item to return
            return_notes: Notes for the return
            condition: Condition of item (ignored if operator is borrower)
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated BorrowRecord
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If no active borrow or permission denied
        """
        from core.role_utils import is_super_admin
        
        # Lock item first, then record (lock ordering invariant)
        item, record = cls._lock_item_then_record(item_id, lock_record=True)
        
        # Validate there is an active borrow
        if not record:
            raise BusinessConflictError(
                code='NO_ACTIVE_BORROW',
                message='This item is not currently borrowed.',
                details={'item_id': item_id}
            )
        
        # Determine operator's relationship to the borrow
        is_owner = item.owner_id == operator.id
        is_admin = is_super_admin(operator)
        is_borrower = record.borrower_id == operator.id
        
        # Validate permission
        if not (is_owner or is_admin or is_borrower):
            raise BusinessConflictError(
                code='PERMISSION_DENIED',
                message='Only the owner, admin, or current borrower can return this item.',
                details={'item_id': item_id}
            )
        
        # Capture states before change
        item_before = cls._get_item_audit_data(item)
        record_before = cls._get_borrow_audit_data(record)
        
        # Update borrow record
        record.actual_return_datetime = timezone.now()
        record.return_notes = return_notes
        record.status = BorrowStatus.RETURNED
        
        # Only owner/admin can set condition
        # Borrower self-return cannot set condition
        if is_owner or is_admin:
            record.condition = condition
        # else: condition remains empty (borrower cannot set it)
        
        record.save()
        
        # Update item status based on remaining borrowed quantity
        # Refresh to get accurate borrowed_quantity after updating record
        item.refresh_from_db()
        if item.borrowed_quantity == 0:
            item.status = ItemStatus.AVAILABLE
        else:
            item.status = ItemStatus.BORROWED
        item.save(update_fields=['status', 'updated_at'])
        
        # Determine operator role for audit
        if is_borrower and not (is_owner or is_admin):
            audit_operator_role = 'borrower'
        else:
            audit_operator_role = getattr(operator, 'role', '')
        
        # Create audit log for return action
        # Note: operator_role is stored as a dedicated field to distinguish
        # borrower self-return from owner/admin return
        audit_log = AuditLog.objects.create(
            action=AuditAction.RETURN,
            target_type=TargetType.ITEM,
            target_id=item.id,
            diff={'before': item_before, 'after': cls._get_item_audit_data(item)},
            operator=operator,
            operator_role=audit_operator_role,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Create audit log for borrow record update
        cls._create_audit_log(
            action=AuditAction.UPDATE,
            target_type=TargetType.BORROW_RECORD,
            target_id=record.id,
            before=record_before,
            after=cls._get_borrow_audit_data(record),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return record
    
    @classmethod
    def get_recent_borrowers(
        cls,
        owner: Optional[User] = None,
        limit: int = 10
    ) -> List[User]:
        """
        Get recent unique active borrowers, most recent first.

        ``owner=None`` returns borrowers across all inventory, which matches
        the current role model (Item.owner is responsibility metadata, not an
        authorization boundary). Passing an owner keeps the old per-owner
        behaviour.

        Uses a single GROUP BY query instead of iterating every borrow record
        in Python.
        """
        from django.db.models import Max

        qs = BorrowRecord.objects.all()
        if owner is not None:
            qs = qs.filter(item__owner_id=owner.id)

        rows = (
            qs.values('borrower_id')
            .annotate(last_borrowed=Max('created_at'))
            .order_by('-last_borrowed')[:limit]
        )
        ordered_ids = [row['borrower_id'] for row in rows]
        users = {
            user.id: user
            for user in User.objects.filter(id__in=ordered_ids, is_active=True)
        }
        return [users[user_id] for user_id in ordered_ids if user_id in users]
    
    @classmethod
    def get_active_borrow(cls, item_id: int) -> Optional[BorrowRecord]:
        """
        Get the active borrow record for an item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            BorrowRecord if item is borrowed, None otherwise
        """
        return BorrowRecord.objects.filter(
            item_id=item_id,
            status=BorrowStatus.ACTIVE
        ).select_related('borrower', 'operator').first()
    
    @classmethod
    def list_records(
        cls,
        item_id: Optional[int] = None,
        borrower_id: Optional[int] = None,
        status: Optional[str] = None,
        owner_id: Optional[int] = None,
        visible_borrower_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QuerySet:
        """
        List borrow records with optional filters.
        
        Args:
            item_id: Filter by item ID
            borrower_id: Filter by borrower ID (用户主动筛选)
            status: Filter by status ('active', 'returned')
            owner_id: Filter by item owner ID (for data isolation)
            visible_borrower_id: 用户作为借用人可见的记录 (与 owner_id 是 OR 关系)
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            
        Returns:
            QuerySet of BorrowRecord
        """
        from django.db.models import Q
        
        qs = BorrowRecord.objects.select_related(
            'item', 'item__owner', 'borrower', 'operator'
        )
        
        if item_id:
            qs = qs.filter(item_id=item_id)
        
        if borrower_id:
            qs = qs.filter(borrower_id=borrower_id)
        
        if status:
            qs = qs.filter(status=status)
        
        # 数据隔离：owner_id 和 visible_borrower_id 是 OR 关系
        # 用户可以看到自己拥有的物品记录 或 自己作为借用人的记录
        if owner_id and visible_borrower_id:
            qs = qs.filter(Q(item__owner_id=owner_id) | Q(borrower_id=visible_borrower_id))
        elif owner_id:
            qs = qs.filter(item__owner_id=owner_id)
        elif visible_borrower_id:
            qs = qs.filter(borrower_id=visible_borrower_id)
        
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        
        return qs.order_by('-created_at')
