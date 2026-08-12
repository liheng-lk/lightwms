"""Permission-hardened inventory views.

These wrappers keep the existing business behavior while centralising role and
owner checks. They intentionally return 404 for another manager's item so the
API does not disclose object existence across manager scopes.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin
from core.role_utils import is_super_admin, is_item_manager, can_manage_item

from .models import Item
from .services import ItemService
from .views import (
    ItemListCreateView as BaseItemListCreateView,
    ItemDetailView as BaseItemDetailView,
    ItemDeactivateView as BaseItemDeactivateView,
    ItemDeleteView as BaseItemDeleteView,
    ItemGenerateBarcodeView as BaseItemGenerateBarcodeView,
    ItemImageListCreateView as BaseItemImageListCreateView,
    ItemImageDetailView as BaseItemImageDetailView,
    ItemImageSetPrimaryView as BaseItemImageSetPrimaryView,
    ItemBatchDeleteView as BaseItemBatchDeleteView,
    ItemCreateWithInvoiceView as BaseItemCreateWithInvoiceView,
    ItemBatchUpdateLocationView as BaseItemBatchUpdateLocationView,
    ItemBatchUpdateOwnerView as BaseItemBatchUpdateOwnerView,
)


class ItemListCreateView(BaseItemListCreateView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        include_inactive = (
            self.request.query_params.get('include_inactive', '').lower() == 'true'
        )

        if include_inactive and is_super_admin(user):
            qs = ItemService.list_all()
        else:
            qs = ItemService.list_active()

        # Managers operate in their own ownership scope. Ordinary users may
        # browse all active inventory, but cannot mutate it.
        if is_item_manager(user):
            qs = qs.filter(owner_id=user.id)

        return qs.prefetch_related('images')


class _OwnedItemMixin:
    """Manager sees only owned items; super admin sees all; ordinary read is allowed."""

    def get_object(self, pk, user):
        try:
            item = Item.objects.select_related(
                'category', 'location', 'location__warehouse', 'owner'
            ).prefetch_related('images').get(pk=pk)
        except Item.DoesNotExist:
            return None

        if is_item_manager(user) and item.owner_id != user.id:
            return None
        return item


class ItemDetailView(_OwnedItemMixin, BaseItemDetailView):
    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT', 'DELETE'):
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]


class ItemDeactivateView(BaseItemDeactivateView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not can_manage_item(request.user, item):
            return Response(
                {'code': 'PERMISSION_DENIED', 'message': 'Permission denied.', 'details': None},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().post(request, pk)


class ItemDeleteView(BaseItemDeleteView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def delete(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not can_manage_item(request.user, item):
            return Response(
                {'code': 'PERMISSION_DENIED', 'message': 'Permission denied.', 'details': None},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().delete(request, pk)


class ItemGenerateBarcodeView(BaseItemGenerateBarcodeView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not can_manage_item(request.user, item):
            return Response(
                {'code': 'PERMISSION_DENIED', 'message': 'Permission denied.', 'details': None},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().post(request, pk)


class ItemImageListCreateView(BaseItemImageListCreateView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]


class ItemImageDetailView(BaseItemImageDetailView):
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]


class ItemImageSetPrimaryView(BaseItemImageSetPrimaryView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemCreateWithInvoiceView(BaseItemCreateWithInvoiceView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemBatchDeleteView(BaseItemBatchDeleteView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemBatchUpdateLocationView(BaseItemBatchUpdateLocationView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemBatchUpdateOwnerView(BaseItemBatchUpdateOwnerView):
    # Reassigning ownership changes another manager's security boundary, so it
    # is a system-administration operation rather than normal stock handling.
    permission_classes = [IsSuperAdmin]
