"""Strict query-contract wrappers for operation ledger lists."""
from rest_framework import serializers, status
from rest_framework.response import Response

from core.pagination import StandardPagination
from core.role_utils import is_item_manager, is_read_only_user

from .models import BorrowStatus
from .permission_views import (
    BorrowRecordListView as BaseBorrowRecordListView,
    TakeRecordListView as BaseTakeRecordListView,
    ReplenishRecordListView as BaseReplenishRecordListView,
)
from .serializers import BorrowRecordSerializer, TakeRecordSerializer, ReplenishRecordSerializer
from .services import BorrowService, ConsumableService


MAX_BIGINT_ID = 9_223_372_036_854_775_807


class DateRangeQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {'end_date': ['end_date must be on or after start_date.']}
            )
        return attrs


class BorrowRecordQuerySerializer(DateRangeQuerySerializer):
    item = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    borrower = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    status = serializers.ChoiceField(required=False, choices=BorrowStatus.choices)


class TakeRecordQuerySerializer(DateRangeQuerySerializer):
    item = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    taker = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)


class ReplenishRecordQuerySerializer(DateRangeQuerySerializer):
    item = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)
    operator = serializers.IntegerField(required=False, min_value=1, max_value=MAX_BIGINT_ID)


def _invalid_query(errors):
    return Response(
        {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid operation record filters.',
            'details': errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _paginate(request, records, serializer_class):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(records, request)
    if page is not None:
        return paginator.get_paginated_response(serializer_class(page, many=True).data)
    return Response(serializer_class(records, many=True).data, status=status.HTTP_200_OK)


class BorrowRecordListView(BaseBorrowRecordListView):
    def get(self, request):
        query = BorrowRecordQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid_query(query.errors)
        data = query.validated_data

        borrower_id = data.get('borrower')
        owner_id = request.user.id if is_item_manager(request.user) else None
        visible_borrower_id = request.user.id if is_read_only_user(request.user) else None
        if is_read_only_user(request.user):
            borrower_id = request.user.id

        records = BorrowService.list_records(
            item_id=data.get('item'),
            borrower_id=borrower_id,
            status=data.get('status'),
            owner_id=owner_id,
            visible_borrower_id=visible_borrower_id,
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
        )
        return _paginate(request, records, BorrowRecordSerializer)


class TakeRecordListView(BaseTakeRecordListView):
    def get(self, request):
        query = TakeRecordQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid_query(query.errors)
        data = query.validated_data

        taker_id = data.get('taker')
        owner_id = request.user.id if is_item_manager(request.user) else None
        visible_taker_id = request.user.id if is_read_only_user(request.user) else None
        if is_read_only_user(request.user):
            taker_id = request.user.id

        records = ConsumableService.list_take_records(
            item_id=data.get('item'),
            taker_id=taker_id,
            owner_id=owner_id,
            visible_taker_id=visible_taker_id,
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
        )
        return _paginate(request, records, TakeRecordSerializer)


class ReplenishRecordListView(BaseReplenishRecordListView):
    def get(self, request):
        query = ReplenishRecordQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid_query(query.errors)
        data = query.validated_data

        owner_id = request.user.id if is_item_manager(request.user) else None
        records = ConsumableService.list_replenish_records(
            item_id=data.get('item'),
            operator_id=data.get('operator'),
            owner_id=owner_id,
            visible_operator_id=None,
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
        )
        return _paginate(request, records, ReplenishRecordSerializer)
