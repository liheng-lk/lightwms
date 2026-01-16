"""
Core views for LightWMS.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for readiness probes.
    Returns 200 if the service is healthy.
    """
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    
    return Response({
        'status': 'ok' if db_status == 'ok' else 'degraded',
        'database': db_status,
    })
