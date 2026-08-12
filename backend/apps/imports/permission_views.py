"""Permission-hardened import/export endpoints.

Bulk exports can contain inventory-wide operational data and user contact
fields, so they are management capabilities rather than ordinary read access.
"""
from rest_framework import status
from rest_framework.response import Response

from core.exceptions import BusinessConflictError
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin

from .serializers import ImportRequestSerializer, ImportResultSerializer
from .services.hardened_import_service import HardenedImportService
from .views import (
    ItemImportView as BaseItemImportView,
    ItemExportView as BaseItemExportView,
    ItemImportTemplateView as BaseItemImportTemplateView,
    BorrowRecordExportView as BaseBorrowRecordExportView,
    TakeRecordExportView as BaseTakeRecordExportView,
    ReplenishRecordExportView as BaseReplenishRecordExportView,
)


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


class ItemImportTemplateView(BaseItemImportTemplateView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class BorrowRecordExportView(BaseBorrowRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class TakeRecordExportView(BaseTakeRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ReplenishRecordExportView(BaseReplenishRecordExportView):
    permission_classes = [IsItemManagerOrSuperAdmin]
