"""Permission-hardened operation views."""
from datetime import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import Item
from core.pagination import StandardPagination
from core.permissions import IsItemManagerOrSuperAdmin
from core.role_utils import is_super_admin, is_item_manager, is_read_only_user

from .models import BorrowRecord, BorrowStatus
from .serializers import BorrowRecordSerializer, TakeRecordSerializer, ReplenishRecordSerializer
from .services import BorrowService, ConsumableService
from .views import (
    ItemBorrowView as BaseItemBorrowView,
    ItemReturnView as BaseItemReturnView,
    BorrowRecordListView as BaseBorrowRecordListView,
    RecentBorrowersView as BaseRecentBorrowersView,
    ItemTakeView as BaseItemTakeView,
    ItemReplenishView as BaseItemReplenishView,
    TakeRecordListView as BaseTakeRecordListView,
    ReplenishRecordListView as BaseReplenishRecordListView,
)


def _owned_item(pk, user):
    try:
        item = Item.objects.select_related('owner', 'location', 'location__warehouse').get(pk=pk)
    except Item.DoesNotExist:
        return None
    if is_item_manager(user) and item.owner_id != user.id:
        return None
    return item


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


class ItemBorrowView(BaseItemBorrowView):
    """Only the responsible manager or super admin can register a borrow."""
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _owned_item(pk, user)


class ItemReturnView(BaseItemReturnView):
    """Owner manager/admin or the current borrower may return an item."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        active = BorrowRecord.objects.filter(
            item_id=pk, status=BorrowStatus.ACTIVE
        ).select_related('borrower').first()

        allowed = (
            is_super_admin(request.user)
            or (is_item_manager(request.user) and item.owner_id == request.user.id)
            or (active is not None and active.borrower_id == request.user.id)
        )
        if not allowed:
            # Do not disclose another manager/user's active transaction.
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, pk)

    def check_return_permission(self, item, user):
        # The explicit relation check above is authoritative; keep base flow happy.
        return True, None


class BorrowRecordListView(BaseBorrowRecordListView):
    """Admin: all; manager: owned items; ordinary user: own borrows."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item')
        borrower_id = request.query_params.get('borrower')
        status_filter = request.query_params.get('status')

        owner_id = request.user.id if is_item_manager(request.user) else None
        visible_borrower_id = request.user.id if is_read_only_user(request.user) else None

        # Ordinary users cannot use borrower= to inspect another person's records.
        if is_read_only_user(request.user):
            borrower_id = request.user.id

        records = BorrowService.list_records(
            item_id=int(item_id) if item_id else None,
            borrower_id=int(borrower_id) if borrower_id else None,
            status=status_filter,
            owner_id=owner_id,
            visible_borrower_id=visible_borrower_id,
            start_date=_parse_date(request.query_params.get('start_date')),
            end_date=_parse_date(request.query_params.get('end_date')),
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            return paginator.get_paginated_response(BorrowRecordSerializer(page, many=True).data)
        return Response(BorrowRecordSerializer(records, many=True).data)


class RecentBorrowersView(BaseRecentBorrowersView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemTakeView(BaseItemTakeView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _owned_item(pk, user)


class ItemReplenishView(BaseItemReplenishView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _owned_item(pk, user)


class TakeRecordListView(BaseTakeRecordListView):
    """Admin: all; manager: owned items; ordinary user: own takes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item')
        taker_id = request.query_params.get('taker')
        owner_id = request.user.id if is_item_manager(request.user) else None
        visible_taker_id = request.user.id if is_read_only_user(request.user) else None
        if is_read_only_user(request.user):
            taker_id = request.user.id

        records = ConsumableService.list_take_records(
            item_id=int(item_id) if item_id else None,
            taker_id=int(taker_id) if taker_id else None,
            owner_id=owner_id,
            visible_taker_id=visible_taker_id,
            start_date=_parse_date(request.query_params.get('start_date')),
            end_date=_parse_date(request.query_params.get('end_date')),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            return paginator.get_paginated_response(TakeRecordSerializer(page, many=True).data)
        return Response(TakeRecordSerializer(records, many=True).data)


class ReplenishRecordListView(BaseReplenishRecordListView):
    """Replenishment is an inventory-management record, not an end-user record."""
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        item_id = request.query_params.get('item')
        operator_id = request.query_params.get('operator')
        owner_id = request.user.id if is_item_manager(request.user) else None
        records = ConsumableService.list_replenish_records(
            item_id=int(item_id) if item_id else None,
            operator_id=int(operator_id) if operator_id else None,
            owner_id=owner_id,
            visible_operator_id=None,
            start_date=_parse_date(request.query_params.get('start_date')),
            end_date=_parse_date(request.query_params.get('end_date')),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            return paginator.get_paginated_response(ReplenishRecordSerializer(page, many=True).data)
        return Response(ReplenishRecordSerializer(records, many=True).data)
