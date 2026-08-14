"""Quantity-aware borrowing and precise return selection."""
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item, ItemStatus, ItemType
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User
from core.exceptions import BusinessConflictError
from core.role_utils import is_item_manager, is_super_admin

from .borrow_service import BorrowService


class QuantityBorrowService(BorrowService):
    """Borrow service consistent with reusable Item.quantity > 1."""

    @classmethod
    def _active_records_locked(cls, item_id: int):
        return list(
            BorrowRecord.objects.select_for_update()
            .filter(item_id=item_id, status=BorrowStatus.ACTIVE)
            .select_related('borrower', 'operator')
            .order_by('id')
        )

    @classmethod
    def _sync_item_status(cls, item: Item) -> None:
        """Status means fully unavailable vs at least one borrowable unit."""
        desired = (
            ItemStatus.BORROWED
            if item.available_quantity == 0
            else ItemStatus.AVAILABLE
        )
        if item.status != desired:
            item.status = desired
            item.save(update_fields=['status', 'updated_at'])

    @classmethod
    @transaction.atomic
    def borrow(
        cls,
        item_id: int,
        borrower_id: int,
        expected_return_date,
        notes: str,
        operator: User,
        quantity: int = 1,
        ip: Optional[str] = None,
        user_agent: str = '',
    ) -> BorrowRecord:
        # Item row is the serialization point for concurrent quantity changes.
        item = Item.objects.select_for_update().get(id=item_id)

        if not item.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot borrow inactive item.',
                details={'item_id': item.id},
            )
        if item.type != ItemType.REUSABLE:
            raise BusinessConflictError(
                code='INVALID_ITEM_TYPE',
                message='Only reusable items can be borrowed.',
                details={'item_id': item.id, 'type': item.type},
            )
        if quantity < 1:
            raise BusinessConflictError(
                code='INVALID_QUANTITY',
                message='Quantity must be at least 1.',
                details={'quantity': quantity},
            )

        active_records = cls._active_records_locked(item_id)
        available = item.available_quantity
        if available < quantity:
            # Preserve the established semantic for a one-unit asset while
            # using quantity language for depleted multi-unit assets.
            if item.quantity == 1 and active_records:
                raise BusinessConflictError(
                    code='ITEM_ALREADY_BORROWED',
                    message='This item is already borrowed.',
                    details={'item_id': item.id},
                )
            raise BusinessConflictError(
                code='INSUFFICIENT_QUANTITY',
                message=f'Not enough available quantity. Available: {available}, Requested: {quantity}',
                details={
                    'item_id': item.id,
                    'available': available,
                    'requested': quantity,
                },
            )

        borrower = cls._validate_borrower(borrower_id)
        item_before = cls._get_item_audit_data(item)

        record = BorrowRecord.objects.create(
            item=item,
            borrower=borrower,
            operator=operator,
            expected_return_date=expected_return_date,
            notes=notes,
            quantity=quantity,
            status=BorrowStatus.ACTIVE,
        )

        item.refresh_from_db()
        cls._sync_item_status(item)

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
    def _resolve_return_record(
        cls,
        *,
        item: Item,
        active_records: list[BorrowRecord],
        operator: User,
        borrow_record_id: Optional[int],
    ) -> BorrowRecord:
        can_manage_returns = is_super_admin(operator) or is_item_manager(operator)

        if borrow_record_id is not None:
            record = next(
                (record for record in active_records if record.id == borrow_record_id),
                None,
            )
            if record is None:
                raise BusinessConflictError(
                    code='BORROW_RECORD_NOT_ACTIVE',
                    message='The selected borrow record is not active for this item.',
                    details={'borrow_record_id': borrow_record_id, 'item_id': item.id},
                )
            if not (can_manage_returns or record.borrower_id == operator.id):
                raise BusinessConflictError(
                    code='PERMISSION_DENIED',
                    message='You cannot return another user\'s borrow record.',
                    details={'borrow_record_id': record.id},
                )
            return record

        if can_manage_returns:
            if len(active_records) == 1:
                return active_records[0]
            raise BusinessConflictError(
                code='BORROW_RECORD_REQUIRED',
                message='Multiple active borrow records exist. Select the record to return.',
                details={
                    'item_id': item.id,
                    'active_record_ids': [record.id for record in active_records],
                },
            )

        own_records = [
            record for record in active_records
            if record.borrower_id == operator.id
        ]
        if len(own_records) == 1:
            return own_records[0]
        if len(own_records) > 1:
            raise BusinessConflictError(
                code='BORROW_RECORD_REQUIRED',
                message='You have multiple active borrow records. Select the record to return.',
                details={
                    'item_id': item.id,
                    'active_record_ids': [record.id for record in own_records],
                },
            )
        raise BusinessConflictError(
            code='PERMISSION_DENIED',
            message='Only an inventory manager, super admin, or borrower can return this item.',
            details={'item_id': item.id},
        )

    @classmethod
    @transaction.atomic
    def return_item(
        cls,
        item_id: int,
        return_notes: str,
        condition: str,
        operator: User,
        borrow_record_id: Optional[int] = None,
        ip: Optional[str] = None,
        user_agent: str = '',
    ) -> BorrowRecord:
        item = Item.objects.select_for_update().get(id=item_id)
        active_records = cls._active_records_locked(item_id)
        if not active_records:
            raise BusinessConflictError(
                code='NO_ACTIVE_BORROW',
                message='This item has no active borrow record.',
                details={'item_id': item_id},
            )

        record = cls._resolve_return_record(
            item=item,
            active_records=active_records,
            operator=operator,
            borrow_record_id=borrow_record_id,
        )

        can_manage_returns = is_super_admin(operator) or is_item_manager(operator)
        is_borrower = record.borrower_id == operator.id
        item_before = cls._get_item_audit_data(item)
        record_before = cls._get_borrow_audit_data(record)

        record.actual_return_datetime = timezone.now()
        record.return_notes = return_notes
        record.status = BorrowStatus.RETURNED
        if can_manage_returns:
            record.condition = condition
        record.save(update_fields=[
            'actual_return_datetime',
            'return_notes',
            'status',
            'condition',
            'updated_at',
        ])

        item.refresh_from_db()
        cls._sync_item_status(item)

        audit_operator_role = (
            'borrower'
            if is_borrower and not can_manage_returns
            else getattr(operator, 'role', '')
        )
        AuditLog.objects.create(
            action=AuditAction.RETURN,
            target_type=TargetType.ITEM,
            target_id=item.id,
            diff={'before': item_before, 'after': cls._get_item_audit_data(item)},
            operator=operator,
            operator_role=audit_operator_role,
            ip=ip,
            user_agent=user_agent,
        )
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
