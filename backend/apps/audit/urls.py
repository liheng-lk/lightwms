"""
URL configuration for audit app.
"""
from django.urls import path
from .views import (
    AuditLogListView,
    AuditLogResourceHistoryView,
    AuditLogUserActivityView,
    LoginLogListView,
)

urlpatterns = [
    # Audit logs
    path('audit-logs/', AuditLogListView.as_view(), name='audit-log-list'),
    path(
        'audit-logs/resource/<str:type>/<int:id>/',
        AuditLogResourceHistoryView.as_view(),
        name='audit-log-resource-history'
    ),
    path(
        'audit-logs/user/<int:id>/',
        AuditLogUserActivityView.as_view(),
        name='audit-log-user-activity'
    ),
    
    # Login logs
    path('login-logs/', LoginLogListView.as_view(), name='login-log-list'),
]
