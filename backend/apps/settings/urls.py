"""
URL configuration for system settings.
"""
from django.urls import path
from .views import SystemSettingsView, LogoUploadView
from .version_views import VersionCheckView
from .webhook_views import (
    WebhookEndpointListCreateView,
    WebhookEndpointDetailView,
    WebhookEndpointTestView,
    WebhookEventListView,
)

urlpatterns = [
    path('', SystemSettingsView.as_view(), name='system-settings'),
    path('upload-logo/', LogoUploadView.as_view(), name='upload-logo'),
    path('version/', VersionCheckView.as_view(), name='version-check'),

    # Webhook endpoints
    path('webhooks/', WebhookEndpointListCreateView.as_view(), name='webhook-list-create'),
    path('webhooks/events/', WebhookEventListView.as_view(), name='webhook-events'),
    path('webhooks/<int:pk>/', WebhookEndpointDetailView.as_view(), name='webhook-detail'),
    path('webhooks/<int:pk>/test/', WebhookEndpointTestView.as_view(), name='webhook-test'),
]
