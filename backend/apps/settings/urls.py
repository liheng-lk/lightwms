"""
URL configuration for system settings.
"""
from django.urls import path
from .views import SystemSettingsView, LogoUploadView

urlpatterns = [
    path('', SystemSettingsView.as_view(), name='system-settings'),
    path('upload-logo/', LogoUploadView.as_view(), name='upload-logo'),
]
