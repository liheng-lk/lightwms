"""Borrow-aware inventory read views."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.role_utils import is_item_manager

from .borrow_serializers import BorrowAwareBarcodeSerializer, BorrowAwareItemSerializer
from .models import Item
from .permission_views import ItemDetailView as BaseItemDetailView


class ItemDetailView(BaseItemDetailView):
    """Item detail including role-scoped active borrow records."""

    def get(self, request, pk):
        item = self.get_object(pk, request.user)
        if item is None:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            BorrowAwareItemSerializer(item, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class ItemByBarcodeView(APIView):
    """Scanner lookup with the same borrow contract as item detail."""
    permission_classes = [IsAuthenticated]

    def get(self, request, barcode):
        try:
            item = (
                Item.objects.select_related('location', 'location__warehouse', 'owner')
                .prefetch_related('images')
                .get(barcode=barcode, is_active=True)
            )
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        if is_item_manager(request.user) and item.owner_id != request.user.id:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            BorrowAwareBarcodeSerializer(item, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
