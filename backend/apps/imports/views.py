"""
Views for import/export operations.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsSuperAdmin
from core.exceptions import BusinessConflictError

from apps.inventory.models import Item
from apps.operations.models import BorrowRecord, TakeRecord, ReplenishRecord

from .services import ImportService, ExportService
from .serializers import (
    ImportRequestSerializer,
    ImportResultSerializer,
    ExportRequestSerializer,
)


class ItemImportView(APIView):
    """Import items from CSV/XLSX file."""
    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'allow_partial': {'type': 'boolean', 'default': True},
                },
                'required': ['file'],
            }
        },
        responses={
            200: ImportResultSerializer,
            400: OpenApiResponse(description='Validation error'),
            409: OpenApiResponse(description='File too large or too many rows'),
        },
        tags=['Import/Export'],
        summary='Import items from CSV/XLSX',
        description='Import items from a CSV or XLSX file. SKU is used as the natural key for upsert.',
    )
    def post(self, request):
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        allow_partial = serializer.validated_data.get('allow_partial', True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            result = ImportService.import_items(
                file_content=uploaded_file.read(),
                file_name=uploaded_file.name,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
                allow_partial=allow_partial,
            )
            
            response_serializer = ImportResultSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except BusinessConflictError as e:
            return Response(
                {'code': e.default_code, 'message': str(e.detail), 'details': e.details},
                status=status.HTTP_409_CONFLICT if e.status_code == 409 else status.HTTP_400_BAD_REQUEST
            )


class ItemExportView(APIView):
    """Export items to CSV/XLSX file."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='file_format', description='Export format (csv or xlsx)', required=False, type=str, default='csv'),
            OpenApiParameter(name='category', description='Filter by category ID', required=False, type=int),
            OpenApiParameter(name='location', description='Filter by location ID', required=False, type=int),
            OpenApiParameter(name='warehouse', description='Filter by warehouse ID', required=False, type=int),
            OpenApiParameter(name='owner', description='Filter by owner ID', required=False, type=int),
            OpenApiParameter(name='type', description='Filter by type (reusable/consumable)', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='include_inactive', description='Include inactive items', required=False, type=bool),
        ],
        responses={
            200: OpenApiResponse(description='File download'),
            409: OpenApiResponse(description='Too many rows'),
        },
        tags=['Import/Export'],
        summary='Export items to CSV/XLSX',
        description='Export items to a CSV or XLSX file with optional filters.',
    )
    def get(self, request):
        # Build queryset with filters
        queryset = Item.objects.all()
        user = request.user
        
        # Data isolation for Item_Manager
        if getattr(user, 'role', None) == 'item_manager':
            queryset = queryset.filter(owner_id=user.id)
        
        # Apply filters
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if not include_inactive or getattr(user, 'role', None) != 'super_admin':
            queryset = queryset.filter(is_active=True)
        
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        location_id = request.query_params.get('location')
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        warehouse_id = request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(location__warehouse_id=warehouse_id)
        
        owner_id = request.query_params.get('owner')
        if owner_id and getattr(user, 'role', None) == 'super_admin':
            queryset = queryset.filter(owner_id=owner_id)
        
        item_type = request.query_params.get('type')
        if item_type:
            queryset = queryset.filter(type=item_type)
        
        item_status = request.query_params.get('status')
        if item_status:
            queryset = queryset.filter(status=item_status)
        
        # Determine format (use file_format to avoid conflict with DRF's format parameter)
        export_format = request.query_params.get('file_format', 'csv').lower()
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            if export_format == 'xlsx':
                content = ExportService.export_items_xlsx(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'items.xlsx'
            else:
                content = ExportService.export_items_csv(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'text/csv; charset=utf-8'
                filename = 'items.csv'
            
            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except BusinessConflictError as e:
            return Response(
                {'code': e.default_code, 'message': str(e.detail), 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ItemImportTemplateView(APIView):
    """Download import template."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='file_format', description='Template format (csv or xlsx)', required=False, type=str, default='csv'),
        ],
        responses={200: OpenApiResponse(description='Template file download')},
        tags=['Import/Export'],
        summary='Download import template',
        description='Download a template file for item import.',
    )
    def get(self, request):
        export_format = request.query_params.get('file_format', 'csv').lower()
        
        if export_format == 'xlsx':
            content = ImportService.generate_import_template_xlsx()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'import_template.xlsx'
        else:
            content = ImportService.generate_import_template_csv()
            content_type = 'text/csv; charset=utf-8'
            filename = 'import_template.csv'
        
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class BorrowRecordExportView(APIView):
    """Export borrow records to CSV/XLSX file."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='file_format', description='Export format (csv or xlsx)', required=False, type=str, default='csv'),
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='borrower', description='Filter by borrower ID', required=False, type=int),
            OpenApiParameter(name='status', description='Filter by status (active/returned)', required=False, type=str),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description='File download'),
            409: OpenApiResponse(description='Too many rows'),
        },
        tags=['Import/Export'],
        summary='Export borrow records',
    )
    def get(self, request):
        queryset = BorrowRecord.objects.all()
        user = request.user
        
        # Data isolation for Item_Manager
        if getattr(user, 'role', None) == 'item_manager':
            queryset = queryset.filter(item__owner_id=user.id)
        
        # Apply filters
        item_id = request.query_params.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        borrower_id = request.query_params.get('borrower')
        if borrower_id:
            queryset = queryset.filter(borrower_id=borrower_id)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Use file_format to avoid conflict with DRF's format parameter
        export_format = request.query_params.get('file_format', 'csv').lower()
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            if export_format == 'xlsx':
                content = ExportService.export_borrow_records_xlsx(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'borrow_records.xlsx'
            else:
                content = ExportService.export_borrow_records_csv(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'text/csv; charset=utf-8'
                filename = 'borrow_records.csv'
            
            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except BusinessConflictError as e:
            return Response(
                {'code': e.default_code, 'message': str(e.detail), 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class TakeRecordExportView(APIView):
    """Export take records to CSV/XLSX file."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='file_format', description='Export format (csv or xlsx)', required=False, type=str, default='csv'),
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='taker', description='Filter by taker ID', required=False, type=int),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description='File download'),
            409: OpenApiResponse(description='Too many rows'),
        },
        tags=['Import/Export'],
        summary='Export take records',
    )
    def get(self, request):
        queryset = TakeRecord.objects.all()
        user = request.user
        
        # Data isolation for Item_Manager
        if getattr(user, 'role', None) == 'item_manager':
            queryset = queryset.filter(item__owner_id=user.id)
        
        # Apply filters
        item_id = request.query_params.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        taker_id = request.query_params.get('taker')
        if taker_id:
            queryset = queryset.filter(taker_id=taker_id)
        
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Use file_format to avoid conflict with DRF's format parameter
        export_format = request.query_params.get('file_format', 'csv').lower()
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            if export_format == 'xlsx':
                content = ExportService.export_take_records_xlsx(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'take_records.xlsx'
            else:
                content = ExportService.export_take_records_csv(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'text/csv; charset=utf-8'
                filename = 'take_records.csv'
            
            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except BusinessConflictError as e:
            return Response(
                {'code': e.default_code, 'message': str(e.detail), 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ReplenishRecordExportView(APIView):
    """Export replenish records to CSV/XLSX file."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='file_format', description='Export format (csv or xlsx)', required=False, type=str, default='csv'),
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description='File download'),
            409: OpenApiResponse(description='Too many rows'),
        },
        tags=['Import/Export'],
        summary='Export replenish records',
    )
    def get(self, request):
        queryset = ReplenishRecord.objects.all()
        user = request.user
        
        # Data isolation for Item_Manager
        if getattr(user, 'role', None) == 'item_manager':
            queryset = queryset.filter(item__owner_id=user.id)
        
        # Apply filters
        item_id = request.query_params.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Use file_format to avoid conflict with DRF's format parameter
        export_format = request.query_params.get('file_format', 'csv').lower()
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            if export_format == 'xlsx':
                content = ExportService.export_replenish_records_xlsx(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'replenish_records.xlsx'
            else:
                content = ExportService.export_replenish_records_csv(
                    queryset=queryset,
                    operator=user,
                    ip=ip,
                    user_agent=user_agent,
                )
                content_type = 'text/csv; charset=utf-8'
                filename = 'replenish_records.csv'
            
            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except BusinessConflictError as e:
            return Response(
                {'code': e.default_code, 'message': str(e.detail), 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )
