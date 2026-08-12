"""Input-contract wrappers for inventory creation endpoints."""
from rest_framework import status
from rest_framework.response import Response

from .permission_views import ItemListCreateView as HardenedItemListCreateView
from .atomic_views import ItemCreateWithInvoiceView as AtomicItemCreateWithInvoiceView


def _validate_reusable_quantity(request):
    """Reject explicit reusable quantities below one instead of coercing them."""
    if request.data.get('type') != 'reusable' or 'quantity' not in request.data:
        return None

    raw_quantity = request.data.get('quantity')
    if raw_quantity in (None, ''):
        return None

    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return Response(
            {
                'code': 'INVALID_QUANTITY',
                'message': 'Reusable quantity must be an integer of at least 1.',
                'details': {'quantity': raw_quantity},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity < 1:
        return Response(
            {
                'code': 'INVALID_QUANTITY',
                'message': 'Reusable quantity must be at least 1.',
                'details': {'quantity': quantity},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


class ItemListCreateView(HardenedItemListCreateView):
    def post(self, request):
        quantity_error = _validate_reusable_quantity(request)
        if quantity_error:
            return quantity_error
        return super().post(request)


class ItemCreateWithInvoiceView(AtomicItemCreateWithInvoiceView):
    def post(self, request):
        quantity_error = _validate_reusable_quantity(request)
        if quantity_error:
            return quantity_error
        return super().post(request)
