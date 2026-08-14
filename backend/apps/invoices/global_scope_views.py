"""Final invoice views for the global Item Manager inventory scope."""

from rest_framework import status
from rest_framework.response import Response

from apps.inventory.models import Item
from core.permissions import IsItemManagerOrSuperAdmin

from .hardened_views import InvoiceListCreateView as HardenedInvoiceListCreateView
from .permission_views import InvoiceListCreateView as PermissionInvoiceListCreateView


class InvoiceListCreateView(HardenedInvoiceListCreateView):
    """Allow managers to associate invoices with any existing inventory item."""

    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        raw_item_id = request.data.get('item_id')
        if raw_item_id not in (None, ''):
            try:
                item_id = int(raw_item_id)
                Item.objects.only('id').get(pk=item_id)
            except (TypeError, ValueError, Item.DoesNotExist):
                return Response(
                    {
                        'code': 'ITEM_NOT_FOUND',
                        'message': 'Associated item not found.',
                        'details': None,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Bypass only the obsolete owner-isolation check in the hardened
        # wrapper. The underlying create implementation and service retain all
        # file, amount, audit and transaction validation.
        return PermissionInvoiceListCreateView.post(self, request)
