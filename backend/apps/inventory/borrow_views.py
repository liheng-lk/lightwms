"""Borrow-aware inventory read views."""
from rest_framework import status
from rest_framework.response import Response

from .borrow_serializers import BorrowAwareItemSerializer
from .permission_views import ItemDetailView as BaseItemDetailView


class ItemDetailView(BaseItemDetailView):
    """Item detail including all active borrow records."""

    def get(self, request, pk):
        item = self.get_object(pk, request.user)
        if item is None:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(BorrowAwareItemSerializer(item).data, status=status.HTTP_200_OK)
