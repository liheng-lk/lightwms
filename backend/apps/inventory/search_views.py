"""Validated, privacy-aware inventory search endpoint."""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination

from .borrow_serializers import BorrowAwareItemSerializer, prefetch_active_borrows
from .models import ItemStatus, ItemType
from .services.search_service import SearchFilters, SearchService


class SearchQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        max_length=100,
    )
    category = serializers.IntegerField(required=False, min_value=1)
    location = serializers.IntegerField(required=False, min_value=1)
    owner = serializers.IntegerField(required=False, min_value=1)
    type = serializers.ChoiceField(required=False, choices=ItemType.choices)
    status = serializers.ChoiceField(required=False, choices=ItemStatus.choices)
    include_inactive = serializers.BooleanField(required=False, default=False)


class SearchView(APIView):
    """Search inventory with strict inputs and the same borrow privacy as detail/scan."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = SearchQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(
                {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Invalid search parameters.',
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
