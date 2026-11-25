"""Advanced search endpoint with multi-condition filtering."""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination

from .borrow_serializers import BorrowAwareItemSerializer, prefetch_active_borrows
from .models import ItemStatus, ItemType
from .services.search_service import SearchFilters, SearchService


MAX_BIGINT_ID = 9_223_372_036_854_775_807


class AdvancedSearchQuerySerializer(serializers.Serializer):
    """Serializer for advanced search with extended filter options."""
    keyword = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        max_length=100,
    )
    category = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    location = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    warehouse = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    owner = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    type = serializers.ChoiceField(required=False, choices=ItemType.choices)
    status = serializers.ChoiceField(required=False, choices=ItemStatus.choices)
    include_inactive = serializers.BooleanField(required=False, default=False)

    # Extended filters for advanced search
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    quantity_min = serializers.IntegerField(required=False, min_value=0)
    quantity_max = serializers.IntegerField(required=False, min_value=0)


class AdvancedSearchView(APIView):
    """Advanced search with multi-condition filtering."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = AdvancedSearchQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(
                {
                    'code': 'VALIDATION_ERROR',
                    'message': '搜索参数无效。',
                    'details': query.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = query.validated_data
        filters = SearchFilters(
            category_id=data.get('category'),
            location_id=data.get('location'),
            owner_id=data.get('owner'),
            status=data.get('status'),
            type=data.get('type'),
        )
        queryset = SearchService.search(
            keyword=data.get('keyword'),
            filters=filters,
            user=request.user,
            include_inactive=data.get('include_inactive', False),
        ).prefetch_related('images')

        # Extended filters
        warehouse_id = data.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(location__warehouse_id=warehouse_id)

        date_from = data.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = data.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        quantity_min = data.get('quantity_min')
        if quantity_min is not None:
            queryset = queryset.filter(quantity__gte=quantity_min)

        quantity_max = data.get('quantity_max')
        if quantity_max is not None:
            queryset = queryset.filter(quantity__lte=quantity_max)

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
