"""Input-contract and presentation wrappers for inventory endpoints."""
from rest_framework import serializers, status
from rest_framework.response import Response

from core.pagination import StandardPagination

from .permission_views import ItemListCreateView as HardenedItemListCreateView
from .atomic_views import ItemCreateWithInvoiceView as AtomicItemCreateWithInvoiceView
from .borrow_serializers import BorrowAwareItemSerializer, prefetch_active_borrows
from .models import ItemStatus, ItemType


MAX_BIGINT_ID = 9_223_372_036_854_775_807


class ItemListQuerySerializer(serializers.Serializer):
    category = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    location = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    warehouse = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    owner = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    type = serializers.ChoiceField(required=False, choices=ItemType.choices)
    status = serializers.ChoiceField(required=False, choices=ItemStatus.choices)
    include_inactive = serializers.BooleanField(required=False)


def _validation_error(errors):
    return Response(
        {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid inventory list parameters.',
            'details': errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


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
        query = ItemListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _validation_error(query.errors)
        data = query.validated_data

        queryset = self.get_queryset()

        if data.get('category') is not None:
            queryset = queryset.filter(category_id=data['category'])
        if data.get('location') is not None:
            queryset = queryset.filter(location_id=data['location'])
        if data.get('warehouse') is not None:
            queryset = queryset.filter(location__warehouse_id=data['warehouse'])
        if data.get('type'):
            queryset = queryset.filter(type=data['type'])
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        if data.get('owner') is not None and getattr(request.user, 'role', None) == 'super_admin':
            queryset = queryset.filter(owner_id=data['owner'])

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
