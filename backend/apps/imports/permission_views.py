"""Permission-hardened import/export endpoints.

Bulk exports can contain inventory-wide operational data and user contact
fields, so they are management capabilities rather than ordinary read access.
"""
from core.permissions import IsItemManagerOrSuperAdmin

from .views import (
    ItemExportView as BaseItemExportView,
    ItemImportTemplateView as BaseItemImportTemplateView,
    BorrowRecordExportView as BaseBorrowRecordExportView,
    TakeRecordExportView as BaseTakeRecordExportView,
    ReplenishRecordExportView as BaseReplenishRecordExportView,
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
