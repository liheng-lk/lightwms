"""Permission and lifecycle wrappers for warehouse/location/category data."""

from rest_framework import status
from rest_framework.response import Response

from apps.users.models import User, UserRole
from core.pagination import StandardPagination
from core.role_utils import is_item_manager, is_super_admin

from .models import Category, Location, Warehouse
from .serializers import LocationSerializer
from .services import LocationService
from .views import (
    WarehouseListCreateView as BaseWarehouseListCreateView,
    WarehouseDetailView as BaseWarehouseDetailView,
    WarehouseDeactivateView,
    WarehouseDeleteView,
    WarehouseBatchDeleteView,
    LocationListCreateView as BaseLocationListCreateView,
    LocationTreeView as BaseLocationTreeView,
    LocationDetailView as BaseLocationDetailView,
    LocationDeactivateView,
    CategoryListCreateView as BaseCategoryListCreateView,
    CategoryTreeView,
    CategoryDetailView as BaseCategoryDetailView,
    CategoryDeactivateView,
    CategoryDeleteView,
    CategoryBatchDeleteView,
)


_MANAGEABLE_OWNER_ROLES = {UserRole.SUPER_ADMIN, UserRole.ITEM_MANAGER}


def _not_found(resource: str):
    return Response(
        {'code': 'NOT_FOUND', 'message': f'{resource} not found.', 'details': None},
        status=status.HTTP_404_NOT_FOUND,
    )


def _validate_location_owner(request, raw_owner_id):
    """Validate that a location owner is an active inventory manager."""
    if raw_owner_id in (None, ''):
        return None

    try:
        owner_id = int(raw_owner_id)
    except (TypeError, ValueError):
        return Response(
            {'code': 'INVALID_OWNER', 'message': 'Invalid location owner.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        owner = User.objects.get(pk=owner_id)
    except User.DoesNotExist:
        return Response(
            {'code': 'OWNER_NOT_FOUND', 'message': 'Location owner not found.', 'details': None},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not owner.is_active:
        return Response(
            {'code': 'OWNER_INACTIVE', 'message': 'Location owner must be active.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if owner.role not in _MANAGEABLE_OWNER_ROLES:
        return Response(
            {
                'code': 'INVALID_OWNER_ROLE',
                'message': 'Location owner must be a super admin or item manager.',
                'details': {'owner_id': owner.id, 'role': owner.role},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if is_item_manager(request.user) and owner.id != request.user.id:
        return Response(
            {
                'code': 'PERMISSION_DENIED',
                'message': 'Item managers can only assign locations to themselves.',
                'details': {'owner_id': owner.id},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return None


def _validate_active_parent_location(request):
    raw_parent_id = request.data.get('parent')
    if raw_parent_id in (None, ''):
        return None

    try:
        parent_id = int(raw_parent_id)
    except (TypeError, ValueError):
        return Response(
            {'code': 'INVALID_PARENT', 'message': 'Invalid parent location.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        parent = Location.objects.select_related('warehouse').get(pk=parent_id)
    except Location.DoesNotExist:
        return _not_found('Parent location')

    if not parent.is_active:
        return Response(
            {
                'code': 'PARENT_INACTIVE',
                'message': 'Cannot create a location under an inactive parent.',
                'details': {'parent_id': parent.id},
            },
            status=status.HTTP_409_CONFLICT,
        )

    if not parent.warehouse.is_active:
        return Response(
            {
                'code': 'WAREHOUSE_INACTIVE',
                'message': 'Cannot create a location inside an inactive warehouse.',
                'details': {'warehouse_id': parent.warehouse_id},
            },
            status=status.HTTP_409_CONFLICT,
        )

    return None


def _validate_active_parent_category(request):
    raw_parent_id = request.data.get('parent')
    if raw_parent_id in (None, ''):
        return None

    try:
        parent_id = int(raw_parent_id)
    except (TypeError, ValueError):
        return Response(
            {'code': 'INVALID_PARENT', 'message': 'Invalid parent category.', 'details': None},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        parent = Category.objects.get(pk=parent_id)
    except Category.DoesNotExist:
        return _not_found('Parent category')

    if not parent.is_active:
        return Response(
            {
                'code': 'PARENT_INACTIVE',
                'message': 'Cannot create a category under an inactive parent.',
                'details': {'parent_id': parent.id},
            },
            status=status.HTTP_409_CONFLICT,
        )

    return None


class WarehouseListCreateView(BaseWarehouseListCreateView):
    pass


class WarehouseDetailView(BaseWarehouseDetailView):
    """Inactive warehouses are maintenance-only records for super admins."""

    def get_object(self, pk):
        try:
            warehouse = Warehouse.objects.get(pk=pk)
        except Warehouse.DoesNotExist:
            return None
        if not warehouse.is_active and not is_super_admin(self.request.user):
            return None
        return warehouse


class LocationListCreateView(BaseLocationListCreateView):
    """Hide locations whose own record or parent warehouse is inactive."""

    def get(self, request):
        warehouse_id = request.query_params.get('warehouse')
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if include_inactive and not is_super_admin(request.user):
            include_inactive = False

        queryset = Location.objects.select_related('warehouse', 'parent', 'owner')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if not include_inactive:
            queryset = queryset.filter(is_active=True, warehouse__is_active=True)
        queryset = queryset.order_by('warehouse__code', 'code', 'id')

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = LocationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response(LocationSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        owner_error = _validate_location_owner(request, request.data.get('owner'))
        if owner_error:
            return owner_error
        parent_error = _validate_active_parent_location(request)
        if parent_error:
            return parent_error
        return super().post(request)


class LocationTreeView(BaseLocationTreeView):
    """Default trees exclude locations belonging to inactive warehouses."""

    def get(self, request):
        warehouse_id = request.query_params.get('warehouse')
        if warehouse_id:
            try:
                warehouse = Warehouse.objects.get(pk=int(warehouse_id))
            except (TypeError, ValueError, Warehouse.DoesNotExist):
                return _not_found('Warehouse')
            if not warehouse.is_active and not is_super_admin(request.user):
                return Response([], status=status.HTTP_200_OK)

        response = super().get(request)
        if response.status_code != status.HTTP_200_OK or is_super_admin(request.user):
            return response

        hidden_ids = set(
            Location.objects.filter(warehouse__is_active=False).values_list('id', flat=True)
        )

        def filter_nodes(nodes):
            filtered = []
            for node in nodes:
                if node.get('id') in hidden_ids:
                    continue
                cleaned = dict(node)
                cleaned['children'] = filter_nodes(node.get('children', []))
                filtered.append(cleaned)
            return filtered

        response.data = filter_nodes(response.data)
        return response


class LocationDetailView(BaseLocationDetailView):
    """Inactive locations/warehouses are hidden outside super-admin maintenance."""

    def get_object(self, pk):
        try:
            location = Location.objects.select_related('warehouse', 'parent', 'owner').get(pk=pk)
        except Location.DoesNotExist:
            return None
        if not is_super_admin(self.request.user):
            if not location.is_active or not location.warehouse.is_active:
                return None
        return location

    def patch(self, request, pk):
        location = self.get_object(pk)
        if not location:
            return _not_found('Location')

        if 'owner' in request.data:
            owner_error = _validate_location_owner(request, request.data.get('owner'))
            if owner_error:
                return owner_error

        return super().patch(request, pk)


class CategoryListCreateView(BaseCategoryListCreateView):
    def post(self, request):
        parent_error = _validate_active_parent_category(request)
        if parent_error:
            return parent_error
        return super().post(request)


class CategoryDetailView(BaseCategoryDetailView):
    """Inactive categories are maintenance-only records for super admins."""

    def get_object(self, pk):
        try:
            category = Category.objects.select_related('parent').get(pk=pk)
        except Category.DoesNotExist:
            return None
        if not category.is_active and not is_super_admin(self.request.user):
            return None
        return category
