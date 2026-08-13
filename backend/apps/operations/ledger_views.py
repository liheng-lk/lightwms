"""Auditable administrative deletion for consumable operation ledgers.

Deleting a TakeRecord/ReplenishRecord removes historical presentation data; it
is deliberately *not* a compensating inventory transaction. Current Item
quantity/status are therefore never mutated by these endpoints. Every delete is
captured in immutable AuditLog before the source record disappears.
"""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction, AuditLog, TargetType
from core.permissions import IsSuperAdmin

from .models import ReplenishRecord, TakeRecord


def _client_metadata(request):
    return (
        getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', '')),
        getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', '')),
    )


def _normalise_ids(raw_ids):
    if not isinstance(raw_ids, list) or not raw_ids:
        return None
    try:
        return list(dict.fromkeys(int(record_id) for record_id in raw_ids))
    except (TypeError, ValueError):
        return None


def _take_snapshot(record: TakeRecord):
    return {
        'item_id': record.item_id,
        'taker_id': record.taker_id,
        'operator_id': record.operator_id,
        'quantity': record.quantity,
        'notes': record.notes,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


def _replenish_snapshot(record: ReplenishRecord):
    return {
        'item_id': record.item_id,
        'operator_id': record.operator_id,
        'quantity': record.quantity,
        'notes': record.notes,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


def _write_delete_audit(request, *, target_type, target_id, before):
    ip, user_agent = _client_metadata(request)
    AuditLog.objects.create(
        action=AuditAction.DELETE,
        target_type=target_type,
        target_id=target_id,
        diff={'before': before, 'after': None},
        operator=request.user,
        operator_role=getattr(request.user, 'role', ''),
        ip=ip or None,
        user_agent=user_agent,
    )


class _SingleLedgerDeleteView(APIView):
    permission_classes = [IsSuperAdmin]
    model = None
    target_type = None
    snapshotter = None
    label = 'Record'

    @transaction.atomic
    def delete(self, request, pk):
        try:
            record = self.model.objects.select_for_update().get(pk=pk)
        except self.model.DoesNotExist:
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': f'{self.label} not found.',
                    'details': None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        before = self.snapshotter(record)
        record_id = record.id
        _write_delete_audit(
            request,
            target_type=self.target_type,
            target_id=record_id,
            before=before,
        )
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TakeRecordDeleteView(_SingleLedgerDeleteView):
    model = TakeRecord
    target_type = TargetType.TAKE_RECORD
    snapshotter = staticmethod(_take_snapshot)
    label = 'Take record'


class ReplenishRecordDeleteView(_SingleLedgerDeleteView):
    model = ReplenishRecord
    target_type = TargetType.REPLENISH_RECORD
    snapshotter = staticmethod(_replenish_snapshot)
    label = 'Replenish record'


class _BatchLedgerDeleteView(APIView):
    permission_classes = [IsSuperAdmin]
    model = None
    target_type = None
    snapshotter = None
    label = 'records'

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

        records = list(
            self.model.objects.select_for_update()
            .filter(id__in=ids)
            .order_by('id')
        )
        if len(records) != len(ids):
            found = {record.id for record in records}
            missing = [record_id for record_id in ids if record_id not in found]
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': f'One or more {self.label} were not found.',
                    'details': {'ids': missing},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        for record in records:
            _write_delete_audit(
                request,
                target_type=self.target_type,
                target_id=record.id,
                before=self.snapshotter(record),
            )

        deleted = len(records)
        self.model.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)


class TakeRecordBatchDeleteView(_BatchLedgerDeleteView):
    model = TakeRecord
    target_type = TargetType.TAKE_RECORD
    snapshotter = staticmethod(_take_snapshot)
    label = 'take records'


class ReplenishRecordBatchDeleteView(_BatchLedgerDeleteView):
    model = ReplenishRecord
    target_type = TargetType.REPLENISH_RECORD
    snapshotter = staticmethod(_replenish_snapshot)
    label = 'replenish records'
