"""Permission-hardened operation views."""
from datetime import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import Item
from core.exceptions import BusinessConflictError
from core.pagination import StandardPagination
from core.permissions import IsItemManagerOrSuperAdmin
from core.role_utils import is_read_only_user

from .models import BorrowStatus
from .serializers import (
    BorrowRecordSerializer,
    BorrowRequestSerializer,
    ReturnRequestSerializer,
    TakeRecordSerializer,
    ReplenishRecordSerializer,
    RecentBorrowerSerializer,
)
from .services import BorrowService, ConsumableService
from .services.quantity_borrow_service import QuantityBorrowService
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


def _managed_item(pk):
    try:
        return Item.objects.select_related(
            'owner', 'location', 'location__warehouse'
        ).get(pk=pk)
    except Item.DoesNotExist:
        return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


class ItemBorrowView(BaseItemBorrowView):
    """Item Managers and Super Admins can register borrows for any inventory."""
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _managed_item(pk)

    def post(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BorrowRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        try:
            record = QuantityBorrowService.borrow(
                item_id=pk,
                borrower_id=serializer.validated_data['borrower_id'],
                expected_return_date=serializer.validated_data['expected_return_date'],
                notes=serializer.validated_data.get('notes', ''),
                operator=request.user,
                quantity=serializer.validated_data.get('quantity', 1),
                ip=ip,
                user_agent=user_agent,
            )
        except BusinessConflictError as exc:
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(BorrowRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class ItemReturnView(BaseItemReturnView):
    """Return one precise active borrow record while retaining self-return."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = _managed_item(pk)
        if item is None:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        try:
            record = QuantityBorrowService.return_item(
                item_id=pk,
                borrow_record_id=serializer.validated_data.get('borrow_record_id'),
                return_notes=serializer.validated_data.get('return_notes', ''),
                condition=serializer.validated_data.get('condition', ''),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
        except BusinessConflictError as exc:
            # Avoid disclosing another user's active transaction to ordinary users.
            if exc.code == 'PERMISSION_DENIED' and is_read_only_user(request.user):
                return Response(
                    {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(BorrowRecordSerializer(record).data, status=status.HTTP_200_OK)

    def check_return_permission(self, item, user):
        return True, None


class BorrowRecordListView(BaseBorrowRecordListView):
    """Admin/manager: all records; ordinary user: own borrows."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item')
        borrower_id = request.query_params.get('borrower')
        status_filter = request.query_params.get('status')

        visible_borrower_id = request.user.id if is_read_only_user(request.user) else None
        if is_read_only_user(request.user):
            borrower_id = request.user.id

        records = BorrowService.list_records(
            item_id=int(item_id) if item_id else None,
            borrower_id=int(borrower_id) if borrower_id else None,
            status=status_filter,
            owner_id=None,
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

    def get(self, request):
        try:
            limit = min(max(1, int(request.query_params.get('limit', '10'))), 100)
        except (TypeError, ValueError):
            limit = 10
        # Managers operate on all inventory, so suggest borrowers globally
        # rather than only those of items the manager happens to own.
        borrowers = BorrowService.get_recent_borrowers(owner=None, limit=limit)
        return Response(
            RecentBorrowerSerializer(borrowers, many=True).data,
            status=status.HTTP_200_OK,
        )


class ItemTakeView(BaseItemTakeView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _managed_item(pk)


class ItemReplenishView(BaseItemReplenishView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk, user):
        return _managed_item(pk)


class TakeRecordListView(BaseTakeRecordListView):
    """Admin/manager: all records; ordinary user: own takes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        item_id = request.query_params.get('item')
        taker_id = request.query_params.get('taker')
        visible_taker_id = request.user.id if is_read_only_user(request.user) else None
        if is_read_only_user(request.user):
            taker_id = request.user.id

        records = ConsumableService.list_take_records(
            item_id=int(item_id) if item_id else None,
            taker_id=int(taker_id) if taker_id else None,
            owner_id=None,
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
        records = ConsumableService.list_replenish_records(
            item_id=int(item_id) if item_id else None,
            operator_id=int(operator_id) if operator_id else None,
            owner_id=None,
            visible_operator_id=None,
            start_date=_parse_date(request.query_params.get('start_date')),
            end_date=_parse_date(request.query_params.get('end_date')),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            return paginator.get_paginated_response(ReplenishRecordSerializer(page, many=True).data)
        return Response(ReplenishRecordSerializer(records, many=True).data)
