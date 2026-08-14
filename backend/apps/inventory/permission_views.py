"""Permission-hardened inventory views.

Item Manager is a global inventory-business role. Item ``owner`` remains useful
responsibility metadata, but it must not isolate otherwise active inventory from
an Item Manager. Super Admin retains the extra maintenance capabilities such as
viewing inactive inventory and reassigning owners in bulk.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User, UserRole
from core.exceptions import BusinessConflictError
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin
from core.role_utils import is_super_admin, can_manage_item

from .models import Item, ItemStatus, ItemType
from .serializers import ItemSerializer
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


_MANAGEABLE_OWNER_ROLES = {UserRole.SUPER_ADMIN, UserRole.ITEM_MANAGER}


def _validate_requested_owner(request):
    """Validate an explicit owner assignment before an item is created."""
    raw_owner_id = request.data.get('owner')
    if raw_owner_id in (None, ''):
        return None

    try:
        owner_id = int(raw_owner_id)
    except (TypeError, ValueError):
        return Response(
            {'code': 'INVALID_OWNER', 'message': 'Invalid owner.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        owner = User.objects.get(pk=owner_id)
    except User.DoesNotExist:
        return Response(
            {'code': 'OWNER_NOT_FOUND', 'message': 'Owner not found.', 'details': None},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not owner.is_active:
        return Response(
            {'code': 'OWNER_INACTIVE', 'message': 'Cannot assign inventory to an inactive user.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if owner.role not in _MANAGEABLE_OWNER_ROLES:
        return Response(
            {
                'code': 'INVALID_OWNER_ROLE',
                'message': 'Inventory owner must be a super admin or item manager.',
                'details': {'owner_id': owner.id, 'role': owner.role},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None


def _normalise_item_ids(raw_ids):
    """Return a de-duplicated integer id list or None for invalid input."""
    if not isinstance(raw_ids, list) or not raw_ids:
        return None
    try:
        return list(dict.fromkeys(int(item_id) for item_id in raw_ids))
    except (TypeError, ValueError):
        return None


def _preflight_items(request, item_ids, *, active_only=False):
    """Resolve the entire batch before mutation and reject missing items."""
    qs = Item.objects.filter(id__in=item_ids)
    if active_only:
        qs = qs.filter(is_active=True)
    items = list(qs.select_for_update())

    if len(items) != len(item_ids):
        found = {item.id for item in items}
        missing = [item_id for item_id in item_ids if item_id not in found]
        return None, Response(
            {
                'code': 'ITEM_NOT_FOUND',
                'message': 'One or more items were not found or are inactive.',
                'details': {'item_ids': missing},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return items, None


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

        return qs.prefetch_related('images')

    def post(self, request):
        owner_error = _validate_requested_owner(request)
        if owner_error:
            return owner_error
        return super().post(request)


class _VisibleItemMixin:
    """Hide inactive maintenance records outside Super Admin."""

    def get_object(self, pk, user):
        try:
            item = Item.objects.select_related(
                'category', 'location', 'location__warehouse', 'owner'
            ).prefetch_related('images').get(pk=pk)
        except Item.DoesNotExist:
            return None

        if not item.is_active and not is_super_admin(user):
            return None
        return item


class ItemDetailView(_VisibleItemMixin, BaseItemDetailView):
    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT', 'DELETE'):
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]

    def patch(self, request, pk):
        item = self.get_object(pk, request.user)
        if item is None:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        if item.type == ItemType.CONSUMABLE and 'quantity' in request.data:
            return Response(
                {
                    'code': 'QUANTITY_MANAGED_BY_OPERATIONS',
                    'message': 'Consumable quantity must be changed through take or replenish operations.',
                    'details': None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = super().patch(request, pk)

        if response.status_code == status.HTTP_200_OK and 'quantity' in request.data:
            refreshed = Item.objects.select_related(
                'category', 'location', 'location__warehouse', 'owner'
            ).prefetch_related('images').get(pk=pk)
            if refreshed.type == ItemType.REUSABLE:
                desired_status = (
                    ItemStatus.BORROWED
                    if refreshed.available_quantity == 0
                    else ItemStatus.AVAILABLE
                )
                if refreshed.status != desired_status:
                    refreshed.status = desired_status
                    refreshed.save(update_fields=['status', 'updated_at'])
                response.data = ItemSerializer(refreshed).data

        return response


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
        if item.type == ItemType.REUSABLE and item.borrowed_quantity > 0:
            return Response(
                {
                    'code': 'ITEM_HAS_ACTIVE_BORROWS',
                    'message': 'Return all borrowed quantity before deactivating this item.',
                    'details': {'borrowed_quantity': item.borrowed_quantity},
                },
                status=status.HTTP_409_CONFLICT,
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


class _VisibleImageItemMixin:
    """Apply inactive visibility rules to image subresources."""

    def get_item(self, pk, user):
        try:
            item = Item.objects.select_related('owner').get(pk=pk)
        except Item.DoesNotExist:
            return None
        if not item.is_active and not is_super_admin(user):
            return None
        return item


class ItemImageListCreateView(_VisibleImageItemMixin, BaseItemImageListCreateView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]


class ItemImageDetailView(_VisibleImageItemMixin, BaseItemImageDetailView):
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]


class ItemImageSetPrimaryView(_VisibleImageItemMixin, BaseItemImageSetPrimaryView):
    permission_classes = [IsItemManagerOrSuperAdmin]


class ItemCreateWithInvoiceView(BaseItemCreateWithInvoiceView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        owner_error = _validate_requested_owner(request)
        if owner_error:
            return owner_error

        if 'invoice_file' in request.FILES:
            invoice_amount = request.data.get('invoice_amount')
            invoice_category = request.data.get('invoice_category')
            if invoice_amount in (None, ''):
                return Response(
                    {
                        'code': 'VALIDATION_ERROR',
                        'message': 'invoice_amount is required when uploading invoice.',
                        'details': None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not invoice_category:
                return Response(
                    {
                        'code': 'VALIDATION_ERROR',
                        'message': 'invoice_category is required when uploading invoice.',
                        'details': None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                amount = Decimal(str(invoice_amount))
            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {
                        'code': 'VALIDATION_ERROR',
                        'message': 'invoice_amount must be a valid number.',
                        'details': None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if amount <= 0:
                return Response(
                    {
                        'code': 'VALIDATION_ERROR',
                        'message': 'invoice_amount must be greater than zero.',
                        'details': None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().post(request)


class ItemBatchDeleteView(BaseItemBatchDeleteView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        item_ids = _normalise_item_ids(request.data.get('ids'))
        if item_ids is None:
            return Response(
                {'code': 'NO_IDS', 'message': 'No valid item IDs provided.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        try:
            with transaction.atomic():
                _, preflight_error = _preflight_items(request, item_ids)
                if preflight_error:
                    transaction.set_rollback(True)
                    return preflight_error

                for item_id in item_ids:
                    ItemService.delete(
                        item_id=item_id,
                        operator=request.user,
                        ip=ip,
                        user_agent=user_agent,
                    )
        except BusinessConflictError as exc:
            return Response(
                {'code': exc.code, 'message': exc.message, 'details': exc.details},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemBatchUpdateLocationView(BaseItemBatchUpdateLocationView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        item_ids = _normalise_item_ids(request.data.get('item_ids'))
        if item_ids is None:
            return Response(
                {'code': 'NO_ITEM_IDS', 'message': '请选择要迁移的物品', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _, preflight_error = _preflight_items(
                request, item_ids, active_only=True
            )
            if preflight_error:
                transaction.set_rollback(True)
                return preflight_error

        return super().post(request)


class ItemBatchUpdateOwnerView(BaseItemBatchUpdateOwnerView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        item_ids = _normalise_item_ids(request.data.get('item_ids'))
        if item_ids is None:
            return Response(
                {'code': 'NO_ITEM_IDS', 'message': '请选择要更改的物品', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _, preflight_error = _preflight_items(
                request, item_ids, active_only=True
            )
            if preflight_error:
                transaction.set_rollback(True)
                return preflight_error

        raw_owner_id = request.data.get('owner_id')
        try:
            owner = User.objects.get(pk=int(raw_owner_id))
        except (TypeError, ValueError, User.DoesNotExist):
            return Response(
                {'code': 'USER_NOT_FOUND', 'message': 'Target user not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not owner.is_active:
            return Response(
                {'code': 'USER_INACTIVE', 'message': 'Cannot assign items to inactive user.', 'details': None},
                status=status.HTTP_409_CONFLICT,
            )
        if owner.role not in _MANAGEABLE_OWNER_ROLES:
            return Response(
                {
                    'code': 'INVALID_OWNER_ROLE',
                    'message': 'Inventory owner must be a super admin or item manager.',
                    'details': {'owner_id': owner.id, 'role': owner.role},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().post(request)
