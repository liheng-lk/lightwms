"""Transaction wrappers for inventory endpoints with multi-resource writes."""
from django.db import transaction

from .permission_views import ItemCreateWithInvoiceView as HardenedItemCreateWithInvoiceView


class ItemCreateWithInvoiceView(HardenedItemCreateWithInvoiceView):
    """Create an item and its invoice as one database transaction.

    The underlying view returns a 4xx response for invoice validation/storage
    conflicts instead of propagating an exception. Explicitly mark the atomic
    block for rollback when that happens so the item cannot survive a failed
    invoice creation.
    """

    @transaction.atomic
    def post(self, request):
        response = super().post(request)
        if response.status_code >= 400:
            transaction.set_rollback(True)
        return response
