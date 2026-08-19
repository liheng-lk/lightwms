"""Invoice metadata endpoints used by filters."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsItemManagerOrSuperAdmin
from .models import Invoice


class InvoiceUploadersView(APIView):
    """Return users who have uploaded at least one invoice."""

    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        rows = (
            Invoice.objects.exclude(created_by_id=None)
            .values('created_by_id', 'created_by__username')
            .distinct()
            .order_by('created_by__username', 'created_by_id')
        )
        return Response(
            [
                {'id': row['created_by_id'], 'username': row['created_by__username']}
                for row in rows
            ],
            status=status.HTTP_200_OK,
        )
