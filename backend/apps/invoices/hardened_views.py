"""Functional hardening wrappers for invoice management."""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item
from apps.users.models import UserRole
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin

from .models import Invoice, InvoiceStatus
from .services import InvoiceService
from .views import (
    InvoiceListCreateView as BaseInvoiceListCreateView,
    InvoiceDetailView as BaseInvoiceDetailView,
    InvoiceBatchStatusUpdateView as BaseInvoiceBatchStatusUpdateView,
    InvoiceBatchDeleteView as BaseInvoiceBatchDeleteView,
)


def _normalise_ids(raw_ids):
    if not isinstance(raw_ids, list) or not raw_ids:
        return None
    try:
        return list(dict.fromkeys(int(invoice_id) for invoice_id in raw_ids))
    except (TypeError, ValueError):
        return None


def _client_metadata(request):
    return (
        getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', '')),
        getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', '')),
    )


def _invoice_snapshot(invoice: Invoice):
    return {
        'name': invoice.name,
        'amount': str(invoice.amount),
        'category': invoice.category,
        'custom_type': invoice.custom_type,
        'project': invoice.project,
        'file': invoice.file,
        'original_filename': invoice.original_filename,
        'status': invoice.status,
        'item_id': invoice.item_id,
        'registered_month': invoice.registered_month,
        'created_by_id': invoice.created_by_id,
        'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
    }


def _write_delete_audit(request, invoice: Invoice):
    ip, user_agent = _client_metadata(request)
    AuditLog.objects.create(
        action=AuditAction.DELETE,
        target_type=TargetType.INVOICE,
        target_id=invoice.id,
        diff={'before': _invoice_snapshot(invoice), 'after': None},
        operator=request.user,
        operator_role=getattr(request.user, 'role', ''),
        ip=ip or None,
        user_agent=user_agent,
    )


def _schedule_file_delete(file_path: str):
    if file_path:
        transaction.on_commit(lambda: InvoiceService._delete_file(file_path))


class InvoiceListCreateView(BaseInvoiceListCreateView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        raw_item_id = request.data.get('item_id')
        if raw_item_id not in (None, ''):
            try:
                item_id = int(raw_item_id)
                item = Item.objects.select_related('owner').get(pk=item_id)
            except (TypeError, ValueError, Item.DoesNotExist):
                return Response(
                    {'code': 'ITEM_NOT_FOUND', 'message': 'Associated item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                request.user.role == UserRole.ITEM_MANAGER
                and item.owner_id != request.user.id
            ):
                # Do not disclose another manager's inventory existence.
                return Response(
                    {'code': 'ITEM_NOT_FOUND', 'message': 'Associated item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return super().post(request)


class InvoiceDetailView(BaseInvoiceDetailView):
    """Preserve scoped retrieve/update behavior and make DELETE audit semantic."""

    @transaction.atomic
    def delete(self, request, pk):
        invoice = self.get_object(pk)
        if not invoice:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Base view already contains scoped permission behavior for GET/PATCH;
        # repeat the manager scope check here because deletion bypasses its
        # service wrapper in order to make filesystem cleanup commit-safe.
        if request.user.role == UserRole.ITEM_MANAGER:
            visible = (
                invoice.created_by_id == request.user.id
                or (invoice.item_id and invoice.item.owner_id == request.user.id)
            )
            if not visible:
                return Response(
                    {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )

        file_path = invoice.file
        _write_delete_audit(request, invoice)
        invoice.delete()
        _schedule_file_delete(file_path)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceBatchStatusUpdateView(BaseInvoiceBatchStatusUpdateView):
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def post(self, request):
        ids = _normalise_ids(request.data.get('ids'))
        new_status = request.data.get('status')
        if ids is None:
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        valid_statuses = {choice[0] for choice in InvoiceStatus.choices}
        if new_status not in valid_statuses:
            return Response(
                {
                    'code': 'INVALID_STATUS',
                    'message': f'Invalid status. Must be one of: {", ".join(sorted(valid_statuses))}',
                    'details': None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        locked = list(Invoice.objects.select_for_update().filter(id__in=ids).order_by('id'))
        if len(locked) != len(ids):
            found = {invoice.id for invoice in locked}
            missing = [invoice_id for invoice_id in ids if invoice_id not in found]
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': 'One or more invoices were not found.',
                    'details': {'ids': missing},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        ip, user_agent = _client_metadata(request)
        for invoice in locked:
            InvoiceService.update(
                invoice_id=invoice.id,
                operator=request.user,
                status=new_status,
                ip=ip,
                user_agent=user_agent,
            )
        return Response({'updated': len(locked)}, status=status.HTTP_200_OK)


class InvoiceBatchDeleteView(BaseInvoiceBatchDeleteView):
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def post(self, request):
        ids = _normalise_ids(request.data.get('ids'))
        if ids is None:
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoices = list(
            Invoice.objects.select_for_update()
            .select_related('item', 'created_by')
            .filter(id__in=ids)
            .order_by('id')
        )
        if len(invoices) != len(ids):
            found = {invoice.id for invoice in invoices}
            missing = [invoice_id for invoice_id in ids if invoice_id not in found]
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': 'One or more invoices were not found.',
                    'details': {'ids': missing},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        file_paths = []
        for invoice in invoices:
            _write_delete_audit(request, invoice)
            file_paths.append(invoice.file)

        deleted = len(invoices)
        Invoice.objects.filter(id__in=ids).delete()
        for file_path in file_paths:
            _schedule_file_delete(file_path)

        return Response({'deleted': deleted}, status=status.HTTP_200_OK)
