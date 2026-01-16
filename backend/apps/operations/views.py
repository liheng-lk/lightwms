"""
Views for operations management.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsSuperAdmin, CanBorrowReturn
from core.pagination import StandardPagination
from core.exceptions import BusinessConflictError

from .models import BorrowRecord, TakeRecord, ReplenishRecord, BorrowStatus
from apps.inventory.models import Item, ItemStatus
from .serializers import (
    BorrowRecordSerializer,
    BorrowRequestSerializer,
    ReturnRequestSerializer,
    RecentBorrowerSerializer,
    TakeRecordSerializer,
    TakeRequestSerializer,
    ReplenishRecordSerializer,
    ReplenishRequestSerializer,
)
from .services import BorrowService, ConsumableService


class ItemBorrowView(APIView):
    """Borrow an item."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get item - item_manager can access all items."""
        try:
            item = Item.objects.select_related(
                'owner', 'location', 'location__warehouse'
            ).get(pk=pk)
            
            # item_manager can access all items (no data isolation)
            
            return item
        except Item.DoesNotExist:
            return None
    
    @extend_schema(
        request=BorrowRequestSerializer,
        responses={
            201: BorrowRecordSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Item not found'),
            409: OpenApiResponse(description='Item already borrowed or inactive'),
        },
        tags=['Operations'],
        summary='Borrow an item',
        description='Register a borrow operation for a reusable item. Only the item owner or Super Admin can perform this operation.',
    )
    def post(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can borrow any item (no ownership check)
        
        serializer = BorrowRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            record = BorrowService.borrow(
                item_id=pk,
                borrower_id=serializer.validated_data['borrower_id'],
                expected_return_date=serializer.validated_data['expected_return_date'],
                notes=serializer.validated_data.get('notes', ''),
                operator=request.user,
                quantity=serializer.validated_data.get('quantity', 1),
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = BorrowRecordSerializer(record)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ItemReturnView(APIView):
    """Return a borrowed item."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Get item without permission check."""
        try:
            return Item.objects.select_related(
                'owner', 'location', 'location__warehouse'
            ).prefetch_related('borrow_records').get(pk=pk)
        except Item.DoesNotExist:
            return None
    
    def check_return_permission(self, item, user):
        """Check if user can return this item.
        
        Return permission:
        - super_admin: can return any item
        - item_manager: can return any item (same as super_admin)
        
        Returns: (can_return: bool, error_message: str or None)
        """
        role = getattr(user, 'role', None)
        
        # Super Admin can return any item
        if role == 'super_admin':
            return True, None
        
        # Item Manager can return any item (same permissions as super_admin for operations)
        if role == 'item_manager':
            return True, None
        
        return False, 'You do not have permission to return this item.'
    
    @extend_schema(
        request=ReturnRequestSerializer,
        responses={
            200: BorrowRecordSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Item not found'),
            409: OpenApiResponse(description='Item not borrowed'),
        },
        tags=['Operations'],
        summary='Return a borrowed item',
        description='Register a return operation for a borrowed item. Owner, Super Admin, or current borrower can perform this operation. Note: Borrower cannot set the condition field.',
    )
    def post(self, request, pk):
        item = self.get_object(pk)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check return permission
        can_return, error_message = self.check_return_permission(item, request.user)
        if not can_return:
            return Response(
                {'code': 'PERMISSION_DENIED', 'message': error_message, 'details': None},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            record = BorrowService.return_item(
                item_id=pk,
                return_notes=serializer.validated_data.get('return_notes', ''),
                condition=serializer.validated_data.get('condition', ''),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = BorrowRecordSerializer(record)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class BorrowRecordListView(APIView):
    """List borrow records."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='borrower', description='Filter by borrower ID', required=False, type=int),
            OpenApiParameter(name='status', description='Filter by status (active/returned)', required=False, type=str),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: BorrowRecordSerializer(many=True)},
        tags=['Operations'],
        summary='List borrow records',
        description='List borrow records with optional filters. Item_Manager users only see records for items they own.',
    )
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        
        # Parse filters
        item_id = request.query_params.get('item')
        borrower_id = request.query_params.get('borrower')
        status_filter = request.query_params.get('status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates
        from datetime import datetime
        parsed_start = None
        parsed_end = None
        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 数据隔离：
        # super_admin 和 item_manager 可以看到所有记录
        owner_id = None
        visible_borrower_id = None
        
        records = BorrowService.list_records(
            item_id=int(item_id) if item_id else None,
            borrower_id=int(borrower_id) if borrower_id else None,
            status=status_filter,
            owner_id=owner_id,
            visible_borrower_id=visible_borrower_id,
            start_date=parsed_start,
            end_date=parsed_end,
        )
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            serializer = BorrowRecordSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = BorrowRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecentBorrowersView(APIView):
    """Get recent borrowers for the current user's items."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='limit', description='Maximum number of borrowers to return (default 10)', required=False, type=int),
        ],
        responses={200: RecentBorrowerSerializer(many=True)},
        tags=['Operations'],
        summary='Get recent borrowers',
        description='Get the most recent unique borrowers for items owned by the current user. Only available for Item_Manager and Super_Admin.',
    )
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        
        limit = request.query_params.get('limit', '10')
        try:
            limit = int(limit)
            limit = min(max(1, limit), 100)  # Clamp between 1 and 100
        except ValueError:
            limit = 10
        
        borrowers = BorrowService.get_recent_borrowers(owner=user, limit=limit)
        
        serializer = RecentBorrowerSerializer(borrowers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ItemTakeView(APIView):
    """Take from a consumable item."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get item - item_manager can access all items."""
        try:
            item = Item.objects.select_related(
                'owner', 'location', 'location__warehouse'
            ).get(pk=pk)
            
            # item_manager can access all items (no data isolation)
            
            return item
        except Item.DoesNotExist:
            return None
    
    @extend_schema(
        request=TakeRequestSerializer,
        responses={
            201: TakeRecordSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Item not found'),
            409: OpenApiResponse(description='Insufficient quantity or item inactive'),
        },
        tags=['Operations'],
        summary='Take from a consumable item',
        description='Register a take operation for a consumable item. Only the item owner or Super Admin can perform this operation.',
    )
    def post(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can take from any item (no ownership check)
        
        serializer = TakeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            record = ConsumableService.take(
                item_id=pk,
                taker_id=serializer.validated_data['taker_id'],
                quantity=serializer.validated_data['quantity'],
                notes=serializer.validated_data.get('notes', ''),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = TakeRecordSerializer(record)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ItemReplenishView(APIView):
    """Replenish a consumable item."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get item - item_manager can access all items."""
        try:
            item = Item.objects.select_related(
                'owner', 'location', 'location__warehouse'
            ).get(pk=pk)
            
            # item_manager can access all items (no data isolation)
            
            return item
        except Item.DoesNotExist:
            return None
    
    @extend_schema(
        request=ReplenishRequestSerializer,
        responses={
            201: ReplenishRecordSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Item not found'),
            409: OpenApiResponse(description='Item inactive or not consumable'),
        },
        tags=['Operations'],
        summary='Replenish a consumable item',
        description='Register a replenish operation for a consumable item. Only the item owner or Super Admin can perform this operation.',
    )
    def post(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can replenish any item (no ownership check)
        
        serializer = ReplenishRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            record = ConsumableService.replenish(
                item_id=pk,
                quantity=serializer.validated_data['quantity'],
                notes=serializer.validated_data.get('notes', ''),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = ReplenishRecordSerializer(record)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class TakeRecordListView(APIView):
    """List take records."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='taker', description='Filter by taker ID', required=False, type=int),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: TakeRecordSerializer(many=True)},
        tags=['Operations'],
        summary='List take records',
        description='List take records with optional filters.',
    )
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        
        # Parse filters
        item_id = request.query_params.get('item')
        taker_id = request.query_params.get('taker')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates
        from datetime import datetime
        parsed_start = None
        parsed_end = None
        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 数据隔离：
        # super_admin 和 item_manager 可以看到所有记录
        owner_id = None
        visible_taker_id = None
        
        records = ConsumableService.list_take_records(
            item_id=int(item_id) if item_id else None,
            taker_id=int(taker_id) if taker_id else None,
            owner_id=owner_id,
            visible_taker_id=visible_taker_id,
            start_date=parsed_start,
            end_date=parsed_end,
        )
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            serializer = TakeRecordSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = TakeRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReplenishRecordListView(APIView):
    """List replenish records."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='operator', description='Filter by operator ID', required=False, type=int),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: ReplenishRecordSerializer(many=True)},
        tags=['Operations'],
        summary='List replenish records',
        description='List replenish records with optional filters.',
    )
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        
        # Parse filters
        item_id = request.query_params.get('item')
        operator_id = request.query_params.get('operator')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates
        from datetime import datetime
        parsed_start = None
        parsed_end = None
        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 数据隔离：
        # super_admin 和 item_manager 可以看到所有记录
        owner_id = None
        visible_operator_id = None
        
        records = ConsumableService.list_replenish_records(
            item_id=int(item_id) if item_id else None,
            operator_id=int(operator_id) if operator_id else None,
            owner_id=owner_id,
            visible_operator_id=visible_operator_id,
            start_date=parsed_start,
            end_date=parsed_end,
        )
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            serializer = ReplenishRecordSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ReplenishRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class BorrowRecordDeleteView(APIView):
    """Delete a borrow record."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Record deleted'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Operations'],
        summary='Delete borrow record',
        description='Permanently delete a borrow record. Only Super Admin can perform this operation.',
    )
    def delete(self, request, pk):
        try:
            record = BorrowRecord.objects.select_related('item').get(pk=pk)
        except BorrowRecord.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Borrow record not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Store item reference before deleting record
        item = record.item
        was_active = record.status == BorrowStatus.ACTIVE
        
        record.delete()
        
        # Update item status if the deleted record was active
        if was_active and item:
            # Refresh to get accurate borrowed_quantity after deletion
            item.refresh_from_db()
            if item.borrowed_quantity == 0:
                item.status = ItemStatus.AVAILABLE
                item.save(update_fields=['status', 'updated_at'])
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class TakeRecordDeleteView(APIView):
    """Delete a take record."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Record deleted'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Operations'],
        summary='Delete take record',
        description='Permanently delete a take record. Only Super Admin can perform this operation.',
    )
    def delete(self, request, pk):
        try:
            record = TakeRecord.objects.get(pk=pk)
        except TakeRecord.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Take record not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReplenishRecordDeleteView(APIView):
    """Delete a replenish record."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Record deleted'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Operations'],
        summary='Delete replenish record',
        description='Permanently delete a replenish record. Only Super Admin can perform this operation.',
    )
    def delete(self, request, pk):
        try:
            record = ReplenishRecord.objects.get(pk=pk)
        except ReplenishRecord.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Replenish record not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BorrowRecordBatchDeleteView(APIView):
    """Batch delete borrow records."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'ids': {'type': 'array', 'items': {'type': 'integer'}}}}},
        responses={
            200: OpenApiResponse(description='Records deleted'),
            400: OpenApiResponse(description='Invalid request'),
        },
        tags=['Operations'],
        summary='Batch delete borrow records',
        description='Permanently delete multiple borrow records. Only Super Admin can perform this operation.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get affected items from active records before deletion
        affected_item_ids = list(
            BorrowRecord.objects.filter(
                id__in=ids,
                status=BorrowStatus.ACTIVE
            ).values_list('item_id', flat=True).distinct()
        )
        
        deleted_count, _ = BorrowRecord.objects.filter(id__in=ids).delete()
        
        # Update status for affected items
        for item_id in affected_item_ids:
            try:
                item = Item.objects.get(id=item_id)
                if item.borrowed_quantity == 0:
                    item.status = ItemStatus.AVAILABLE
                    item.save(update_fields=['status', 'updated_at'])
            except Item.DoesNotExist:
                pass
        
        return Response({'deleted': deleted_count}, status=status.HTTP_200_OK)


class TakeRecordBatchDeleteView(APIView):
    """Batch delete take records."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'ids': {'type': 'array', 'items': {'type': 'integer'}}}}},
        responses={
            200: OpenApiResponse(description='Records deleted'),
            400: OpenApiResponse(description='Invalid request'),
        },
        tags=['Operations'],
        summary='Batch delete take records',
        description='Permanently delete multiple take records. Only Super Admin can perform this operation.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted_count, _ = TakeRecord.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted_count}, status=status.HTTP_200_OK)


class ReplenishRecordBatchDeleteView(APIView):
    """Batch delete replenish records."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'ids': {'type': 'array', 'items': {'type': 'integer'}}}}},
        responses={
            200: OpenApiResponse(description='Records deleted'),
            400: OpenApiResponse(description='Invalid request'),
        },
        tags=['Operations'],
        summary='Batch delete replenish records',
        description='Permanently delete multiple replenish records. Only Super Admin can perform this operation.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted_count, _ = ReplenishRecord.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted_count}, status=status.HTTP_200_OK)
