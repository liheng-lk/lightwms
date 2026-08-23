"""
Core views for LightWMS.
"""
from pathlib import PurePosixPath

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import Http404
from django.views.static import serve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Readiness probe for the database and cache dependencies."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    try:
        probe_key = 'lightwms:health:probe'
        cache.set(probe_key, 'ok', timeout=10)
        cache_status = 'ok' if cache.get(probe_key) == 'ok' else 'error'
        cache.delete(probe_key)
    except Exception:
        cache_status = 'error'

    healthy = db_status == 'ok' and cache_status == 'ok'
    return Response(
        {
            'status': 'ok' if healthy else 'degraded',
            'database': db_status,
            'cache': cache_status,
        },
        status=200 if healthy else 503,
    )


def public_media_serve(request, path: str):
    """Serve only non-sensitive media.

    Invoice attachments are private business documents and must go through the
    authenticated invoice endpoint.  Item photos and branding assets remain
    available through the normal media route.
    """
    clean = PurePosixPath(str(path or ''))
    if clean.is_absolute() or '..' in clean.parts or not clean.parts:
        raise Http404
    if clean.parts[0].lower() == 'invoices':
        raise Http404
    return serve(request, clean.as_posix(), document_root=settings.MEDIA_ROOT)
