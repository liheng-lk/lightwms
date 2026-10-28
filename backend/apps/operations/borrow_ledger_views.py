"""Auditable administrative deletion for borrow records.

Replaces the original ``views.BorrowRecordDeleteView`` /
``BorrowRecordBatchDeleteView`` which ran without a transaction or locks,
wrote no audit log, crashed on non-integer ids, and only reset Item.status
when *all* borrowed quantity was gone (leaving multi-quantity items stuck in
``borrowed`` after one active record was removed).

Deleting an *active* record releases its quantity. That is now recorded in the
immutable AuditLog (with the full record snapshot) and the item status is
re-derived from the remaining quantity, exactly as a normal return does.
"""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import TargetType
from apps.inventory.models import Item
from core.permissions import IsSuperAdmin

from .ledger_views import _normalise_ids, _write_delete_audit
from .models import BorrowRecord, BorrowStatus
from .services.quantity_borrow_service import QuantityBorrowService


def _borrow_snapshot(record: BorrowRecord):
    return {
        'item_id': record.item_id,
        'borrower_id': record.borrower_id,
        'operator_id': record.operator_id,
        'quantity': record.quantity,
        'expected_return_date': str(record.expected_return_date),
        'actual_return_datetime': (
            record.actual_return_datetime.isoformat()
            if record.actual_return_datetime else None
        ),
        'notes': record.notes,
        'return_notes': record.return_notes,
        'condition': record.condition,
        'status': record.status,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


def _delete_borrow_records(request, ids):
    """Lock items, then records (same order as BorrowService), audit, delete.

    Returns ``(deleted_count, missing_ids)``. Nothing is deleted when any id is
    missing so the batch is all-or-nothing.
    """
    item_ids = sorted(set(
        BorrowRecord.objects.filter(id__in=ids).values_list('item_id', flat=True)
    ))
    # Item rows are the serialization point for quantity changes.
    items = {
        item.id: item
        for item in Item.objects.select_for_update().filter(id__in=item_ids).order_by('id')
    }

    records = list(
        BorrowRecord.objects.select_for_update().filter(id__in=ids).order_by('id')
    )
    found = {record.id for record in records}
    missing = [record_id for record_id in ids if record_id not in found]
    if missing:
        return 0, missing

    affected_item_ids = {
        record.item_id for record in records if record.status == BorrowStatus.ACTIVE
    }

    for record in records:
        _write_delete_audit(
            request,
            target_type=TargetType.BORROW_RECORD,
            target_id=record.id,
            before=_borrow_snapshot(record),
        )

    BorrowRecord.objects.filter(id__in=[record.id for record in records]).delete()

    for item_id in affected_item_ids:
        item = items.get(item_id)
        if item is not None:
            QuantityBorrowService._sync_item_status(item)

    return len(records), []


class BorrowRecordDeleteView(APIView):
    """Delete one borrow record (Super Admin only)."""
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def delete(self, request, pk):
        deleted, missing = _delete_borrow_records(request, [pk])
        if missing:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Borrow record not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BorrowRecordBatchDeleteView(APIView):
    """Delete several borrow records atomically (Super Admin only)."""
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def post(self, request):
        ids = _normalise_ids(request.data.get('ids'))
        if ids is None:
            return Response(
                {
                    'code': 'INVALID_REQUEST',
                    'message': 'ids must be a non-empty list of integers',
                    'details': None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, missing = _delete_borrow_records(request, ids)
        if missing:
            transaction.set_rollback(True)
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': 'One or more borrow records were not found.',
                    'details': {'ids': missing},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)
