"""
URL configuration for import/export operations.

Note: All import/export routes are now defined in apps.inventory.urls
to avoid URL conflicts and ensure proper routing order.
This file is kept for backwards compatibility but contains no routes.
"""
from django.urls import path

urlpatterns = [
    # All routes moved to apps.inventory.urls
]
