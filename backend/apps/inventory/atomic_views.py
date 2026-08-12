"""Transaction wrappers for inventory endpoints with multi-resource writes."""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from apps.invoices.services import InvoiceService
from core.exceptions import BusinessConflictError

from .permission_views import ItemCreateWithInvoiceView as HardenedItemCreateWithInvoiceView


class ItemCreateWithInvoiceView(HardenedItemCreateWithInvoiceView):
    """Create an item and its optional invoice as one logical operation."""

    @transaction.atomic
    def post(self, request):
        # Validate file type/size before ItemService.create() writes anything.
        # The legacy view catches invoice validation errors after creating the
        # item and turns them into a 201 warning, which is not atomic behavior.
        invoice_file = request.FILES.get('invoice_file')
        if invoice_file is not None:
            try:
                InvoiceService._validate_file(invoice_file, invoice_file.name)
            except BusinessConflictError as exc:
                transaction.set_rollback(True)
                return Response(
                    {'code': exc.code, 'message': exc.message, 'details': exc.details},
                    status=status.HTTP_409_CONFLICT,
                )

        response = super().post(request)

        # Any downstream item/invoice validation response rolls back the item.
        # A remaining invoice_warning would mean invoice creation failed after
        # pre-validation; treat that as failure rather than returning a false
        # success with a partially-created resource.
        invoice_warning = (
            isinstance(getattr(response, 'data', None), dict)
            and response.data.get('invoice_warning')
        )
        if response.status_code >= 400 or invoice_warning:
            transaction.set_rollback(True)
            if invoice_warning and response.status_code < 400:
                return Response(
                    {
                        'code': 'INVOICE_UPLOAD_FAILED',
                        'message': str(invoice_warning),
                        'details': None,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        return response
