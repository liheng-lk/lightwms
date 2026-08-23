"""
URL configuration for LightWMS project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import health_check, public_media_serve
from apps.users.urls import auth_urlpatterns, user_urlpatterns, invite_code_urlpatterns
from apps.operations.urls import item_borrow_urlpatterns, item_consumable_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check endpoint
    path('api/v1/health/', health_check, name='health-check'),

    # Authentication endpoints
    path('api/v1/auth/', include(auth_urlpatterns)),

    # User endpoints
    path('api/v1/users/', include(user_urlpatterns)),

    # Invite code endpoints
    path('api/v1/invite-codes/', include(invite_code_urlpatterns)),

    # Inventory endpoints
    path('api/v1/', include('apps.inventory.urls')),

    # Operations endpoints (borrow records, take records, replenish records, recent borrowers)
    path('api/v1/', include('apps.operations.urls')),

    # Item-specific borrow/return endpoints
    path('api/v1/', include(item_borrow_urlpatterns)),

    # Item-specific take/replenish endpoints
    path('api/v1/', include(item_consumable_urlpatterns)),

    # Audit endpoints
    path('api/v1/', include('apps.audit.urls')),

    # Import/Export endpoints
    path('api/v1/', include('apps.imports.urls')),

    # Invoice endpoints
    path('api/v1/', include('apps.invoices.urls')),

    # System settings endpoints
    path('api/v1/system-settings/', include('apps.settings.urls')),

    # OpenAPI schema and documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Public media only. Invoice attachments are deliberately excluded inside
    # public_media_serve and are available only through authenticated RBAC APIs.
    re_path(r'^media/(?P<path>.*)$', public_media_serve, name='public-media'),
]
