"""Permission-hardened import/export endpoints.

Bulk exports can contain inventory-wide operational data and user contact
fields, so they are management capabilities rather than ordinary read access.
Item Manager is global for active inventory business data; ``owner`` is a
filterable responsibility field, not a permission boundary.
"""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.inventory.models import Item
from apps.operations.models import BorrowRecord, ReplenishRecord, TakeRecord
from core.exceptions import BusinessConflictError
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin
from core.role_utils import is_super_admin

from .serializers import ImportRequestSerializer, ImportResultSerializer
from .services import ExportService
from .services.hardened_import_service import HardenedImportService
from .views import (
    ItemImportView as BaseItemImportView,
    ItemExportView as BaseItemExportView,
    ItemImportTemplateView as BaseItemImportTemplateView,
    BorrowRecordExportView as BaseBorrowRecordExportView,
    TakeRecordExportView as BaseTakeRecordExportView,
    ReplenishRecordExportView as BaseReplenishRecordExportView,
)


def _download(content, content_type, filename):
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _export_error(exc):
    return Response(
        {'code': exc.default_code, 'message': str(exc.detail), 'details': exc.details},
        status=status.HTTP_409_CONFLICT,
    )


def _request_context(request):
    return {
        'operator': request.user,
        'ip': getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', '')),
        'user_agent': getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', '')),
    }


class ItemImportView(BaseItemImportView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        allow_partial = serializer.validated_data.get('allow_partial', True)
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        try:
            result = HardenedImportService.import_items(
                file_content=uploaded_file.read(),
                file_name=uploaded_file.name,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
                allow_partial=allow_partial,
            )
            return Response(
                ImportResultSerializer(result).data,
                status=status.HTTP_200_OK,
            )
        except BusinessConflictError as exc:
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=exc.status_code,
            )


class ItemExportView(BaseItemExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        queryset = Item.objects.all()

        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if not (include_inactive and is_super_admin(request.user)):
            queryset = queryset.filter(is_active=True)

        filter_map = {
            'category': 'category_id',
            'location': 'location_id',
            'warehouse': 'location__warehouse_id',
            'owner': 'owner_id',
            'type': 'type',
            'status': 'status',
        }
        for param, field in filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{field: value})

        export_format = request.query_params.get('file_format', 'csv').lower()
        context = _request_context(request)
        try:
            if export_format == 'xlsx':
                return _download(
                    ExportService.export_items_xlsx(queryset=queryset, **context),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'items.xlsx',
                )
            return _download(
                ExportService.export_items_csv(queryset=queryset, **context),
                'text/csv; charset=utf-8',
                'items.csv',
            )
        except BusinessConflictError as exc:
            return _export_error(exc)


class ItemImportTemplateView(BaseItemImportTemplateView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class BorrowRecordExportView(BaseBorrowRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        queryset = BorrowRecord.objects.all()
        filter_map = {
            'item': 'item_id',
            'borrower': 'borrower_id',
            'status': 'status',
        }
        for param, field in filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{field: value})
        if request.query_params.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=request.query_params['start_date'])
        if request.query_params.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=request.query_params['end_date'])

        export_format = request.query_params.get('file_format', 'csv').lower()
        context = _request_context(request)
        try:
            if export_format == 'xlsx':
                return _download(
                    ExportService.export_borrow_records_xlsx(queryset=queryset, **context),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'borrow_records.xlsx',
                )
            return _download(
                ExportService.export_borrow_records_csv(queryset=queryset, **context),
                'text/csv; charset=utf-8',
                'borrow_records.csv',
            )
        except BusinessConflictError as exc:
            return _export_error(exc)


class TakeRecordExportView(BaseTakeRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        queryset = TakeRecord.objects.all()
        for param, field in {'item': 'item_id', 'taker': 'taker_id'}.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{field: value})
        if request.query_params.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=request.query_params['start_date'])
        if request.query_params.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=request.query_params['end_date'])

        export_format = request.query_params.get('file_format', 'csv').lower()
        context = _request_context(request)
        try:
            if export_format == 'xlsx':
                return _download(
                    ExportService.export_take_records_xlsx(queryset=queryset, **context),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'take_records.xlsx',
                )
            return _download(
                ExportService.export_take_records_csv(queryset=queryset, **context),
                'text/csv; charset=utf-8',
                'take_records.csv',
            )
        except BusinessConflictError as exc:
            return _export_error(exc)


class ReplenishRecordExportView(BaseReplenishRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        queryset = ReplenishRecord.objects.all()
        item_id = request.query_params.get('item')
        if item_id not in (None, ''):
            queryset = queryset.filter(item_id=item_id)
        if request.query_params.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=request.query_params['start_date'])
        if request.query_params.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=request.query_params['end_date'])

        export_format = request.query_params.get('file_format', 'csv').lower()
        context = _request_context(request)
        try:
            if export_format == 'xlsx':
                return _download(
                    ExportService.export_replenish_records_xlsx(queryset=queryset, **context),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'replenish_records.xlsx',
                )
            return _download(
                ExportService.export_replenish_records_csv(queryset=queryset, **context),
                'text/csv; charset=utf-8',
                'replenish_records.csv',
            )
        except BusinessConflictError as exc:
            return _export_error(exc)
