"""Super-admin-only audit endpoints."""
from core.permissions import IsSuperAdmin
from .views import (
    AuditLogListView as BaseAuditLogListView,
    AuditLogResourceHistoryView as BaseAuditLogResourceHistoryView,
    AuditLogUserActivityView as BaseAuditLogUserActivityView,
    LoginLogListView as BaseLoginLogListView,
)


class AuditLogListView(BaseAuditLogListView):
    permission_classes = [IsSuperAdmin]


class AuditLogResourceHistoryView(BaseAuditLogResourceHistoryView):
    permission_classes = [IsSuperAdmin]


class AuditLogUserActivityView(BaseAuditLogUserActivityView):
    permission_classes = [IsSuperAdmin]


class LoginLogListView(BaseLoginLogListView):
    permission_classes = [IsSuperAdmin]
