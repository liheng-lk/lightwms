"""Authenticated access to private invoice attachments."""
from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath

from django.http import FileResponse, Http404
from rest_framework.views import APIView

from core.permissions import IsItemManagerOrSuperAdmin

from .models import Invoice
from .hardened_views import _resolve_invoice_file


class PrivateInvoiceFileView(APIView):
    """Serve one registered invoice attachment after RBAC checks.

    The URL uses the stored invoice-relative path so the existing frontend media
    route can transparently upgrade invoice files from public to authenticated
    access.  The database lookup is exact: an arbitrary file sitting in the
    media volume is never downloadable through this endpoint.
    """

    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request, path: str):
        clean = PurePosixPath(str(path or ''))
        if clean.is_absolute() or '..' in clean.parts or not clean.parts:
            raise Http404

        storage_path = f"invoices/{clean.as_posix()}"
        try:
            invoice = Invoice.objects.only(
                'id', 'file', 'original_filename'
            ).get(file=storage_path)
        except Invoice.DoesNotExist as exc:
            raise Http404 from exc

        resolved = _resolve_invoice_file(invoice.file)
        if not resolved.exists() or not resolved.is_file():
            raise Http404

        content_type = (
            mimetypes.guess_type(invoice.original_filename or invoice.file)[0]
            or 'application/octet-stream'
        )
        response = FileResponse(
            resolved.open('rb'),
            as_attachment=False,
            filename=invoice.original_filename or resolved.name,
            content_type=content_type,
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
