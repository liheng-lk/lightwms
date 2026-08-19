"""
URL configuration for LightWMS project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import health_check, version_check
from apps.users.urls import auth_urlpatterns, user_urlpatterns, invite_code_urlpatterns
from apps.operations.urls import item_borrow_urlpatterns, item_consumable_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/version/', version_check, name='version-check'),

    path('api/v1/auth/', include(auth_urlpatterns)),
    path('api/v1/users/', include(user_urlpatterns)),
    path('api/v1/invite-codes/', include(invite_code_urlpatterns)),
    path('api/v1/', include('apps.inventory.urls')),
    path('api/v1/', include('apps.operations.urls')),
    path('api/v1/', include(item_borrow_urlpatterns)),
    path('api/v1/', include(item_consumable_urlpatterns)),
    path('api/v1/', include('apps.audit.urls')),
    path('api/v1/', include('apps.imports.urls')),
    path('api/v1/', include('apps.invoices.urls')),
    path('api/v1/system-settings/', include('apps.settings.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
