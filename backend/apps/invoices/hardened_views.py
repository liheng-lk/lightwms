"""Functional hardening wrappers for invoice management."""
import io
import os
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item
from apps.users.models import UserRole
from core.exceptions import BusinessConflictError
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin

from .models import Invoice, InvoiceStatus
from .services import InvoiceService
from .permission_views import (
    InvoiceListCreateView as BaseInvoiceListCreateView,
    InvoiceDetailView as BaseInvoiceDetailView,
    InvoiceBatchStatusUpdateView as BaseInvoiceBatchStatusUpdateView,
    InvoiceBatchDeleteView as BaseInvoiceBatchDeleteView,
    InvoiceExportView as BaseInvoiceExportView,
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


def _safe_archive_component(value, fallback='unknown', max_length=60):
    """Return one ZIP path component; never allow separators or dot traversal."""
    value = str(value or '').strip()
    cleaned = ''.join(
        char if (char.isalnum() or char in (' ', '-', '_', '.', '@')) else '_'
        for char in value
    ).strip(' .')
    if cleaned in ('', '.', '..'):
        cleaned = fallback
    return cleaned[:max_length]


def _invoice_archive_filename(invoice: Invoice, ext: str) -> str:
    """Build exported filename as 上传人+发票名称+发票金额.ext."""
    uploader = _safe_archive_component(
        invoice.created_by.username if invoice.created_by else 'unknown',
        fallback='unknown',
    )
    invoice_name = _safe_archive_component(invoice.name, fallback='invoice')
    amount = _safe_archive_component(format(invoice.amount, 'f'), fallback='0.00')
    return f'{uploader}+{invoice_name}+{amount}{ext}'


def _resolve_invoice_file(file_path: str) -> Path:
    """Resolve an invoice file and guarantee it remains below MEDIA_ROOT."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / str(file_path or '')).resolve()
    if not candidate.is_relative_to(media_root):
        raise BusinessConflictError(
            code='INVALID_FILE_PATH',
            message='Invoice file path is outside the media directory.',
            details={'file': str(file_path or '')},
        )
    return candidate


def _export_files_to_safe_zip(invoices) -> bytes:
    output = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for invoice in invoices:
            if not invoice.file:
                continue
            file_path = _resolve_invoice_file(invoice.file)
            if not file_path.exists() or not file_path.is_file():
                continue

            ext = os.path.splitext(invoice.file)[1].lower()
            category = _safe_archive_component(invoice.category, fallback='未分类')
            exported_filename = _invoice_archive_filename(invoice, ext)
            archive_name = f'{category}/{exported_filename}'

            # Exact duplicates are rare but possible. Preserve the requested
            # naming format for the first file and only add a numeric suffix
            # when required to avoid duplicate paths inside the ZIP archive.
            if archive_name in used_names:
                stem, suffix = os.path.splitext(exported_filename)
                duplicate_index = 2
                while f'{category}/{stem}_{duplicate_index}{suffix}' in used_names:
                    duplicate_index += 1
                archive_name = f'{category}/{stem}_{duplicate_index}{suffix}'
            used_names.add(archive_name)
            archive.write(file_path, archive_name)

    output.seek(0)
    return output.read()


class InvoiceListCreateView(BaseInvoiceListCreateView):
    """Keep permission-scoped list/create behavior and harden item association."""
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

            if request.user.role == UserRole.ITEM_MANAGER and item.owner_id != request.user.id:
                # Do not disclose another manager's inventory existence.
                return Response(
                    {'code': 'ITEM_NOT_FOUND', 'message': 'Associated item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return super().post(request)


class InvoiceDetailView(BaseInvoiceDetailView):
    """Preserve scoped GET/PATCH behavior and make deletion commit-safe/auditable."""

    @transaction.atomic
    def delete(self, request, pk):
        invoice = self.get_object(pk)
        if not invoice:
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

        # Lock only Invoice rows. Joining nullable item with FOR UPDATE causes
        # PostgreSQL to reject the query because the nullable side of an outer
        # join cannot be locked.
        invoices = list(
            Invoice.objects.select_for_update()
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


class InvoiceExportView(BaseInvoiceExportView):
    """Super-admin ZIP export with path confinement and strict selected-ID semantics."""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        invoices = InvoiceService.list(
            category=request.query_params.get('category'),
            status=request.query_params.get('status'),
            registered_month=request.query_params.get('month'),
        )
        try:
            content = _export_files_to_safe_zip(invoices)
        except BusinessConflictError as exc:
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=status.HTTP_409_CONFLICT,
            )
        filename = f"invoices_{request.query_params.get('month') or 'all'}.zip"
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def post(self, request):
        ids = _normalise_ids(request.data.get('ids'))
        if ids is None:
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoices = list(
            Invoice.objects.select_related('item', 'created_by')
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

        try:
            content = _export_files_to_safe_zip(invoices)
        except BusinessConflictError as exc:
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=status.HTTP_409_CONFLICT,
            )
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="invoices_selected_{len(ids)}.zip"'
        return response
