"""Input-contract and presentation wrappers for inventory endpoints."""
from rest_framework import status
from rest_framework.response import Response

from core.pagination import StandardPagination

from .permission_views import ItemListCreateView as HardenedItemListCreateView
from .atomic_views import ItemCreateWithInvoiceView as AtomicItemCreateWithInvoiceView
from .borrow_serializers import BorrowAwareItemSerializer, prefetch_active_borrows


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
    def get(self, request):
        queryset = self.get_queryset()

        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        location_id = request.query_params.get('location')
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        warehouse_id = request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(location__warehouse_id=warehouse_id)

        item_type = request.query_params.get('type')
        if item_type:
            queryset = queryset.filter(type=item_type)

        item_status = request.query_params.get('status')
        if item_status:
            queryset = queryset.filter(status=item_status)

        owner_id = request.query_params.get('owner')
        if owner_id and getattr(request.user, 'role', None) == 'super_admin':
            queryset = queryset.filter(owner_id=owner_id)

        queryset = prefetch_active_borrows(queryset)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            payload = BorrowAwareItemSerializer(
                page,
                many=True,
                context={'request': request},
            ).data
            return paginator.get_paginated_response(payload)

        payload = BorrowAwareItemSerializer(
            queryset,
            many=True,
            context={'request': request},
        ).data
        return Response(payload, status=status.HTTP_200_OK)

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
