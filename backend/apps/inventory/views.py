"""
Views for inventory management.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsSuperAdmin, IsItemManagerOrSuperAdmin
from core.pagination import StandardPagination
from core.exceptions import BusinessConflictError

from .models import Warehouse, Location, Category
from .serializers import (
    WarehouseSerializer,
    WarehouseCreateSerializer,
    WarehouseUpdateSerializer,
    LocationSerializer,
    LocationCreateSerializer,
    LocationUpdateSerializer,
    LocationTreeNodeSerializer,
    CategorySerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
    CategoryTreeNodeSerializer,
)
from .services import WarehouseService, LocationService, CategoryService


class WarehouseListCreateView(APIView):
    """List and create warehouses."""
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='include_inactive', description='Include inactive warehouses', required=False, type=bool),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: WarehouseSerializer(many=True)},
        tags=['Warehouses'],
        summary='List warehouses',
    )
    def get(self, request):
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if include_inactive and getattr(request.user, 'role', None) == 'super_admin':
            warehouses = WarehouseService.list_all()
        else:
            warehouses = WarehouseService.list_active()
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(warehouses, request)
        if page is not None:
            serializer = WarehouseSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = WarehouseSerializer(warehouses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=WarehouseCreateSerializer,
        responses={201: WarehouseSerializer, 400: OpenApiResponse(description='Validation error')},
        tags=['Warehouses'],
        summary='Create warehouse',
    )
    def post(self, request):
        serializer = WarehouseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        warehouse = WarehouseService.create(
            code=serializer.validated_data['code'],
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        response_serializer = WarehouseSerializer(warehouse)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class WarehouseDetailView(APIView):
    """Get and update warehouse details."""
    
    def get_permissions(self):
        if self.request.method in ['PATCH', 'PUT']:
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    def get_object(self, pk):
        try:
            return Warehouse.objects.get(pk=pk)
        except Warehouse.DoesNotExist:
            return None
    
    @extend_schema(responses={200: WarehouseSerializer, 404: OpenApiResponse(description='Not found')}, tags=['Warehouses'], summary='Get warehouse')
    def get(self, request, pk):
        warehouse = self.get_object(pk)
        if not warehouse:
            return Response({'code': 'NOT_FOUND', 'message': 'Warehouse not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        serializer = WarehouseSerializer(warehouse)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(request=WarehouseUpdateSerializer, responses={200: WarehouseSerializer}, tags=['Warehouses'], summary='Update warehouse')
    def patch(self, request, pk):
        warehouse = self.get_object(pk)
        if not warehouse:
            return Response({'code': 'NOT_FOUND', 'message': 'Warehouse not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WarehouseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        warehouse = WarehouseService.update(
            warehouse_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
            **serializer.validated_data
        )
        
        response_serializer = WarehouseSerializer(warehouse)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class WarehouseDeactivateView(APIView):
    """Deactivate a warehouse (soft delete)."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(responses={200: WarehouseSerializer, 404: OpenApiResponse(description='Not found')}, tags=['Warehouses'], summary='Deactivate warehouse')
    def post(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            warehouse = WarehouseService.deactivate(
                warehouse_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            serializer = WarehouseSerializer(warehouse)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Warehouse.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Warehouse not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)


class WarehouseDeleteView(APIView):
    """Permanently delete a warehouse (hard delete)."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Warehouse deleted'),
            404: OpenApiResponse(description='Not found'),
            409: OpenApiResponse(description='Has children'),
        },
        tags=['Warehouses'],
        summary='Delete warehouse permanently',
    )
    def delete(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            WarehouseService.delete(
                warehouse_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Warehouse.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Warehouse not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        except BusinessConflictError as e:
            return Response({'code': e.code, 'message': e.message, 'details': e.details}, status=status.HTTP_409_CONFLICT)


class LocationListCreateView(APIView):
    """List and create locations."""
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='warehouse', description='Filter by warehouse ID', required=False, type=int),
            OpenApiParameter(name='include_inactive', description='Include inactive locations', required=False, type=bool),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: LocationSerializer(many=True)},
        tags=['Locations'],
        summary='List locations',
    )
    def get(self, request):
        warehouse_id = request.query_params.get('warehouse')
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        
        if include_inactive and getattr(request.user, 'role', None) != 'super_admin':
            include_inactive = False
        
        queryset = Location.objects.select_related('warehouse', 'parent')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        queryset = queryset.order_by('warehouse__code', 'code', 'id')
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = LocationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = LocationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=LocationCreateSerializer,
        responses={201: LocationSerializer, 400: OpenApiResponse(description='Validation error'), 409: OpenApiResponse(description='Conflict')},
        tags=['Locations'],
        summary='Create location',
    )
    def post(self, request):
        serializer = LocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            location = LocationService.create(
                warehouse_id=serializer.validated_data['warehouse_id'],
                code=serializer.validated_data['code'],
                name=serializer.validated_data['name'],
                owner_id=serializer.validated_data['owner_id'],
                parent_id=serializer.validated_data.get('parent_id'),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = LocationSerializer(location)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Warehouse.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Warehouse not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        except Location.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Parent location not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)


class LocationTreeView(APIView):
    """Get location tree for a warehouse or all warehouses."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='warehouse', description='Warehouse ID (optional, if not provided returns all locations)', required=False, type=int),
            OpenApiParameter(name='include_inactive', description='Include inactive locations', required=False, type=bool),
        ],
        responses={200: LocationTreeNodeSerializer(many=True)},
        tags=['Locations'],
        summary='Get location tree',
    )
    def get(self, request):
        warehouse_id = request.query_params.get('warehouse')
        
        if warehouse_id:
            try:
                warehouse_id = int(warehouse_id)
            except ValueError:
                return Response({'code': 'VALIDATION_ERROR', 'message': 'warehouse must be an integer.', 'details': None}, status=status.HTTP_400_BAD_REQUEST)
        else:
            warehouse_id = None
        
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if include_inactive and getattr(request.user, 'role', None) != 'super_admin':
            include_inactive = False
        
        tree = LocationService.get_tree(warehouse_id=warehouse_id, include_inactive=include_inactive)
        return Response(tree, status=status.HTTP_200_OK)


class LocationDetailView(APIView):
    """Get and update location details."""
    
    def get_permissions(self):
        if self.request.method in ['PATCH', 'PUT']:
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    def get_object(self, pk):
        try:
            return Location.objects.select_related('warehouse', 'parent').get(pk=pk)
        except Location.DoesNotExist:
            return None
    
    @extend_schema(responses={200: LocationSerializer, 404: OpenApiResponse(description='Not found')}, tags=['Locations'], summary='Get location')
    def get(self, request, pk):
        location = self.get_object(pk)
        if not location:
            return Response({'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        serializer = LocationSerializer(location)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(request=LocationUpdateSerializer, responses={200: LocationSerializer}, tags=['Locations'], summary='Update location')
    def patch(self, request, pk):
        location = self.get_object(pk)
        if not location:
            return Response({'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        location = LocationService.update(
            location_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
            **serializer.validated_data
        )
        
        response_serializer = LocationSerializer(location)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LocationDeactivateView(APIView):
    """Deactivate a location (soft delete)."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(
        responses={200: LocationSerializer, 404: OpenApiResponse(description='Not found'), 409: OpenApiResponse(description='Has children or items')},
        tags=['Locations'],
        summary='Deactivate location',
    )
    def post(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            location = LocationService.deactivate(
                location_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            serializer = LocationSerializer(location)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Location.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)



class CategoryListCreateView(APIView):
    """List and create categories."""
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='include_inactive', description='Include inactive categories', required=False, type=bool),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: CategorySerializer(many=True)},
        tags=['Categories'],
        summary='List categories',
    )
    def get(self, request):
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if include_inactive and getattr(request.user, 'role', None) == 'super_admin':
            categories = CategoryService.list_all()
        else:
            categories = CategoryService.list_active()
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(categories, request)
        if page is not None:
            serializer = CategorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=CategoryCreateSerializer,
        responses={201: CategorySerializer, 400: OpenApiResponse(description='Validation error'), 404: OpenApiResponse(description='Parent not found')},
        tags=['Categories'],
        summary='Create category',
    )
    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            category = CategoryService.create(
                name=serializer.validated_data['name'],
                parent_id=serializer.validated_data.get('parent_id'),
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = CategorySerializer(category)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Category.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Parent category not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)


class CategoryTreeView(APIView):
    """Get category tree."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='include_inactive', description='Include inactive categories', required=False, type=bool),
        ],
        responses={200: CategoryTreeNodeSerializer(many=True)},
        tags=['Categories'],
        summary='Get category tree',
    )
    def get(self, request):
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        if include_inactive and getattr(request.user, 'role', None) != 'super_admin':
            include_inactive = False
        
        tree = CategoryService.get_tree(include_inactive=include_inactive)
        return Response(tree, status=status.HTTP_200_OK)


class CategoryDetailView(APIView):
    """Get and update category details."""
    
    def get_permissions(self):
        if self.request.method in ['PATCH', 'PUT']:
            return [IsItemManagerOrSuperAdmin()]
        return [IsAuthenticated()]
    
    def get_object(self, pk):
        try:
            return Category.objects.select_related('parent').get(pk=pk)
        except Category.DoesNotExist:
            return None
    
    @extend_schema(responses={200: CategorySerializer, 404: OpenApiResponse(description='Not found')}, tags=['Categories'], summary='Get category')
    def get(self, request, pk):
        category = self.get_object(pk)
        if not category:
            return Response({'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(request=CategoryUpdateSerializer, responses={200: CategorySerializer}, tags=['Categories'], summary='Update category')
    def patch(self, request, pk):
        category = self.get_object(pk)
        if not category:
            return Response({'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CategoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        category = CategoryService.update(
            category_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
            **serializer.validated_data
        )
        
        response_serializer = CategorySerializer(category)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class CategoryDeactivateView(APIView):
    """Deactivate a category (soft delete)."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(
        responses={200: CategorySerializer, 404: OpenApiResponse(description='Not found'), 409: OpenApiResponse(description='Has children or items')},
        tags=['Categories'],
        summary='Deactivate category',
    )
    def post(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            category = CategoryService.deactivate(
                category_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            serializer = CategorySerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)


class CategoryDeleteView(APIView):
    """Permanently delete a category (hard delete)."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Category deleted'),
            404: OpenApiResponse(description='Not found'),
            409: OpenApiResponse(description='Has children or items'),
        },
        tags=['Categories'],
        summary='Delete category permanently',
    )
    def delete(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            CategoryService.delete(
                category_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Category.DoesNotExist:
            return Response({'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None}, status=status.HTTP_404_NOT_FOUND)
        except BusinessConflictError as e:
            return Response({'code': e.code, 'message': e.message, 'details': e.details}, status=status.HTTP_409_CONFLICT)


from .models import Item
from .serializers import (
    ItemSerializer,
    ItemCreateSerializer,
    ItemUpdateSerializer,
    BarcodeLabelSerializer,
)
from .services import ItemService, ItemCreateDTO, ItemUpdateDTO
from core.permissions import IsItemOwner
from core.mixins import DataIsolationMixin


class ItemListCreateView(APIView):
    """List and create items."""
    
    def get_permissions(self):
        if self.request.method == 'POST':
            # Item_Manager and Super_Admin can create items
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Get queryset with data isolation."""
        user = self.request.user
        include_inactive = self.request.query_params.get('include_inactive', '').lower() == 'true'
        
        # Base queryset
        if include_inactive and getattr(user, 'role', None) == 'super_admin':
            qs = ItemService.list_all()
        else:
            qs = ItemService.list_active()
        
        # item_manager can see all items (no data isolation)
        
        # Prefetch images for primary_image field
        qs = qs.prefetch_related('images')
        
        return qs
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='include_inactive', description='Include inactive items (Super_Admin only)', required=False, type=bool),
            OpenApiParameter(name='category', description='Filter by category ID', required=False, type=int),
            OpenApiParameter(name='location', description='Filter by location ID', required=False, type=int),
            OpenApiParameter(name='warehouse', description='Filter by warehouse ID', required=False, type=int),
            OpenApiParameter(name='type', description='Filter by type (reusable/consumable)', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='owner', description='Filter by owner ID', required=False, type=int),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: ItemSerializer(many=True)},
        tags=['Items'],
        summary='List items',
    )
    def get(self, request):
        queryset = self.get_queryset()
        
        # Apply filters
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        location_id = request.query_params.get('location')
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        warehouse_id = request.query_params.get('warehouse')
        if warehouse_id:
            queryset = queryset.filter(location__warehouse_id=warehouse_id)
        
        item_type = request.query_params.get('type')
        if item_type:
            queryset = queryset.filter(type=item_type)
        
        item_status = request.query_params.get('status')
        if item_status:
            queryset = queryset.filter(status=item_status)
        
        owner_id = request.query_params.get('owner')
        if owner_id and getattr(request.user, 'role', None) == 'super_admin':
            queryset = queryset.filter(owner_id=owner_id)
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=ItemCreateSerializer,
        responses={201: ItemSerializer, 400: OpenApiResponse(description='Validation error'), 409: OpenApiResponse(description='Conflict')},
        tags=['Items'],
        summary='Create item',
    )
    def post(self, request):
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        data = serializer.validated_data
        dto = ItemCreateDTO(
            name=data['name'],
            sku=data['sku'],
            location_id=data['location_id'],
            type=data.get('type', 'reusable'),
            barcode=data.get('barcode'),
            category_id=data.get('category_id'),
            unit=data.get('unit', ''),
            description=data.get('description', ''),
            owner_id=data.get('owner_id'),
            quantity=data.get('quantity'),
        )
        
        try:
            item = ItemService.create(
                data=dto,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = ItemSerializer(item)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Location.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except Category.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )


class ItemDetailView(APIView):
    """Get and update item details."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get item - item_manager can access all items."""
        try:
            item = Item.objects.select_related(
                'category', 'location', 'location__warehouse', 'owner'
            ).prefetch_related('images').get(pk=pk)
            
            # item_manager can access all items (no data isolation)
            
            return item
        except Item.DoesNotExist:
            return None
    
    @extend_schema(
        responses={200: ItemSerializer, 404: OpenApiResponse(description='Not found')},
        tags=['Items'],
        summary='Get item',
    )
    def get(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=ItemUpdateSerializer,
        responses={200: ItemSerializer, 403: OpenApiResponse(description='Permission denied'), 404: OpenApiResponse(description='Not found')},
        tags=['Items'],
        summary='Update item',
    )
    def patch(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can update all items (no ownership check)
        
        serializer = ItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        data = serializer.validated_data
        dto = ItemUpdateDTO(
            name=data.get('name'),
            barcode=data.get('barcode'),
            category_id=data.get('category_id'),
            unit=data.get('unit'),
            description=data.get('description'),
            location_id=data.get('location_id'),
            quantity=data.get('quantity'),
        )
        
        try:
            item = ItemService.update(
                item_id=pk,
                data=dto,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = ItemSerializer(item)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Location.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except Category.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Item deleted'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Items'],
        summary='Delete item permanently',
    )
    def delete(self, request, pk):
        item = self.get_object(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can delete all items (no ownership check)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        ItemService.delete(
            item_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemDeactivateView(APIView):
    """Deactivate an item (soft delete)."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: ItemSerializer, 403: OpenApiResponse(description='Permission denied'), 404: OpenApiResponse(description='Not found')},
        tags=['Items'],
        summary='Deactivate item',
    )
    def post(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can deactivate all items (no ownership check)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        item = ItemService.deactivate(
            item_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        serializer = ItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ItemDeleteView(APIView):
    """Permanently delete an item (hard delete)."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Item deleted'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
            409: OpenApiResponse(description='Item has related records'),
        },
        tags=['Items'],
        summary='Delete item permanently',
    )
    def delete(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can delete all items (no ownership check)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            ItemService.delete(
                item_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemGenerateBarcodeView(APIView):
    """Generate barcode for an item."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: BarcodeLabelSerializer,
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
            409: OpenApiResponse(description='Barcode generation failed'),
        },
        tags=['Items'],
        summary='Generate barcode',
    )
    def post(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can generate barcodes for all items (no ownership check)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        result = ItemService.generate_barcode(
            item_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        serializer = BarcodeLabelSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


from .serializers import ItemByBarcodeSerializer


class ItemByBarcodeView(APIView):
    """
    Get item by barcode for mobile scanner.
    
    GET /api/v1/items/by-barcode/{barcode}/
    
    Returns item details including type, status, quantity for quick operations.
    
    Implements Requirements 3.1, 3.2, 3.3
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: ItemByBarcodeSerializer,
            404: OpenApiResponse(description='Item not found'),
        },
        tags=['Items'],
        summary='Get item by barcode',
        description='''
Lookup an item by its barcode for mobile scanner operations.

Returns item details including:
- Basic info: id, name, sku, barcode
- Type and status for determining available operations
- Quantity (for consumable items)
- Location path and owner info
- Primary image thumbnail

**Data Isolation:**
- Super_Admin: can lookup any item
- Item_Manager: can lookup any item
        '''
    )
    def get(self, request, barcode):
        """Get item by barcode."""
        try:
            item = Item.objects.select_related(
                'location', 'location__warehouse', 'owner'
            ).prefetch_related('images').get(barcode=barcode, is_active=True)
            
            # Data isolation for Item_Manager
            if getattr(request.user, 'role', None) == 'item_manager' and item.owner_id != request.user.id:
                return Response(
                    {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ItemByBarcodeSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Item.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )


from .services import SearchService, SearchFilters


class SearchView(APIView):
    """
    Search items with keyword and filters.
    
    GET /api/v1/search/
    
    Query Parameters:
        - keyword: Search keyword (optional, 1-100 chars)
        - category: Filter by category ID
        - location: Filter by location ID
        - owner: Filter by owner ID (Super_Admin only)
        - status: Filter by status (available/borrowed/in_stock/out_of_stock)
        - type: Filter by type (reusable/consumable)
        - include_inactive: Include inactive items (Super_Admin only)
        - page: Page number
        - page_size: Results per page
    
    Implements Requirements 11.1-11.11
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='keyword',
                description='Search keyword (1-100 characters). Searches name, SKU, and barcode.',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='category',
                description='Filter by category ID',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='location',
                description='Filter by location ID',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='owner',
                description='Filter by owner ID (Super_Admin only)',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='status',
                description='Filter by status (available/borrowed/in_stock/out_of_stock)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='type',
                description='Filter by type (reusable/consumable)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='include_inactive',
                description='Include inactive items (Super_Admin only)',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='page_size',
                description='Results per page (max 100)',
                required=False,
                type=int
            ),
        ],
        responses={200: ItemSerializer(many=True)},
        tags=['Search'],
        summary='Search items',
        description='''
Search items with keyword and filters.

**Ranking Priority:**
1. Exact SKU match (case-insensitive) - highest priority
2. SKU prefix match
3. Name FTS rank
4. Barcode match
5. Trigram similarity - lowest priority

**Tie-breaker:** updated_at desc, id desc

**Data Isolation:**
- Super_Admin: sees all items
- Item_Manager: sees all items
        '''
    )
    def get(self, request):
        # Parse query parameters
        keyword = request.query_params.get('keyword')
        
        # Parse filter parameters
        category_id = request.query_params.get('category')
        location_id = request.query_params.get('location')
        owner_id = request.query_params.get('owner')
        item_status = request.query_params.get('status')
        item_type = request.query_params.get('type')
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        
        # Build filters
        filters = SearchFilters(
            category_id=int(category_id) if category_id else None,
            location_id=int(location_id) if location_id else None,
            owner_id=int(owner_id) if owner_id else None,
            status=item_status if item_status else None,
            type=item_type if item_type else None,
        )
        
        # Execute search
        queryset = SearchService.search(
            keyword=keyword,
            filters=filters,
            user=request.user,
            include_inactive=include_inactive,
        )
        
        # Paginate results
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



from .models import ItemImage
from .serializers import ItemImageSerializer, ImageUploadSerializer
from .services import ImageService


class ItemImageListCreateView(APIView):
    """
    List and upload images for an item.
    
    GET /api/v1/items/{id}/images/
    POST /api/v1/items/{id}/images/
    
    Implements Requirements 12.1-12.13
    """
    permission_classes = [IsAuthenticated]
    
    def get_item(self, pk, user):
        """Get item with permission check."""
        try:
            item = Item.objects.select_related('owner').get(pk=pk)
            
            # Data isolation for Item_Manager
            if getattr(user, 'role', None) == 'item_manager' and item.owner_id != user.id:
                return None
            
            return item
        except Item.DoesNotExist:
            return None
    
    @extend_schema(
        responses={200: ItemImageSerializer(many=True), 404: OpenApiResponse(description='Item not found')},
        tags=['Item Images'],
        summary='List item images',
    )
    def get(self, request, pk):
        """List all images for an item."""
        item = self.get_item(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        images = ImageService.list_by_item(pk)
        serializer = ItemImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request={'multipart/form-data': ImageUploadSerializer},
        responses={
            201: ItemImageSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Item not found'),
            409: OpenApiResponse(description='Conflict'),
        },
        tags=['Item Images'],
        summary='Upload item image',
        description='''
Upload an image for an item.

**Image Processing:**
- Original image is converted to WebP format (max 2000px dimension)
- Three thumbnails are generated: 256px, 768px, 1600px
- EXIF orientation is auto-corrected
- Quality: 85 for all WebP outputs

**Constraints:**
- Max file size: 10MB
- Allowed formats: JPEG, PNG, GIF, WebP, BMP, TIFF
- Only one image per item can be primary
        '''
    )
    def post(self, request, pk):
        """Upload a new image for an item."""
        item = self.get_item(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can upload images for all items (no ownership check)
        
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        result = ImageService.upload(
            item_id=pk,
            file=serializer.validated_data['image'],
            is_primary=serializer.validated_data.get('is_primary', False),
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        response_serializer = ItemImageSerializer(result.image, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ItemImageDetailView(APIView):
    """
    Get and delete a specific image.
    
    GET /api/v1/items/{item_id}/images/{image_id}/
    DELETE /api/v1/items/{item_id}/images/{image_id}/
    
    Implements Requirements 12.9, 12.13
    """
    permission_classes = [IsAuthenticated]
    
    def get_item(self, pk, user):
        """Get item with permission check."""
        try:
            item = Item.objects.select_related('owner').get(pk=pk)
            
            # Data isolation for Item_Manager
            if getattr(user, 'role', None) == 'item_manager' and item.owner_id != user.id:
                return None
            
            return item
        except Item.DoesNotExist:
            return None
    
    def get_image(self, item_id, image_id):
        """Get image belonging to item."""
        try:
            return ItemImage.objects.get(id=image_id, item_id=item_id)
        except ItemImage.DoesNotExist:
            return None
    
    @extend_schema(
        responses={200: ItemImageSerializer, 404: OpenApiResponse(description='Not found')},
        tags=['Item Images'],
        summary='Get item image',
    )
    def get(self, request, pk, image_id):
        """Get a specific image."""
        item = self.get_item(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        image = self.get_image(pk, image_id)
        if not image:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Image not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ItemImageSerializer(image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Image deleted'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Item Images'],
        summary='Delete item image',
        description='''
Delete an image and all associated files.

If the deleted image was the primary image and other images exist,
the most recently uploaded image becomes the new primary.
        '''
    )
    def delete(self, request, pk, image_id):
        """Delete an image."""
        item = self.get_item(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can delete images for all items (no ownership check)
        
        image = self.get_image(pk, image_id)
        if not image:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Image not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        ImageService.delete(
            image_id=image_id,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemImageSetPrimaryView(APIView):
    """
    Set an image as the primary image for an item.
    
    POST /api/v1/items/{item_id}/images/{image_id}/set-primary/
    
    Implements Requirements 12.11, 12.12
    """
    permission_classes = [IsAuthenticated]
    
    def get_item(self, pk, user):
        """Get item with permission check."""
        try:
            item = Item.objects.select_related('owner').get(pk=pk)
            
            # Data isolation for Item_Manager
            if getattr(user, 'role', None) == 'item_manager' and item.owner_id != user.id:
                return None
            
            return item
        except Item.DoesNotExist:
            return None
    
    def get_image(self, item_id, image_id):
        """Get image belonging to item."""
        try:
            return ItemImage.objects.get(id=image_id, item_id=item_id)
        except ItemImage.DoesNotExist:
            return None
    
    @extend_schema(
        responses={
            200: ItemImageSerializer,
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Item Images'],
        summary='Set primary image',
        description='Set an image as the primary image for an item. Only one image per item can be primary.'
    )
    def post(self, request, pk, image_id):
        """Set an image as primary."""
        item = self.get_item(pk, request.user)
        if not item:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Item not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # item_manager can modify images for all items (no ownership check)
        
        image = self.get_image(pk, image_id)
        if not image:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Image not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        image = ImageService.set_primary(
            image_id=image_id,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        
        serializer = ItemImageSerializer(image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)



from rest_framework.parsers import MultiPartParser, FormParser


class ItemCreateWithInvoiceView(APIView):
    """
    Create an item with optional invoice upload.
    
    POST /api/v1/items/with-invoice/
    
    This endpoint supports multipart form data for creating an item
    with an optional invoice file attachment.
    
    Implements Requirements 23.1, 23.2
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'Item name'},
                    'sku': {'type': 'string', 'description': 'Item SKU'},
                    'barcode': {'type': 'string', 'description': 'Item barcode (optional)'},
                    'category': {'type': 'integer', 'description': 'Category ID (optional)'},
                    'unit': {'type': 'string', 'description': 'Unit (optional)'},
                    'description': {'type': 'string', 'description': 'Description (optional)'},
                    'location': {'type': 'integer', 'description': 'Location ID'},
                    'owner': {'type': 'integer', 'description': 'Owner ID (optional)'},
                    'type': {'type': 'string', 'enum': ['reusable', 'consumable'], 'description': 'Item type'},
                    'quantity': {'type': 'integer', 'description': 'Quantity (for consumable items)'},
                    'invoice_file': {'type': 'string', 'format': 'binary', 'description': 'Invoice file (PDF, JPG, PNG) - optional'},
                    'invoice_amount': {'type': 'number', 'description': 'Invoice amount (required if invoice_file provided)'},
                    'invoice_category': {'type': 'string', 'description': 'Invoice category (required if invoice_file provided)'},
                    'invoice_custom_type': {'type': 'string', 'description': 'Invoice custom type (optional)'},
                },
                'required': ['name', 'sku', 'location', 'type'],
            }
        },
        responses={
            201: ItemSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            409: OpenApiResponse(description='Conflict'),
        },
        tags=['Items'],
        summary='Create item with invoice',
        description='Create a new item with optional invoice file upload. The invoice will be automatically associated with the item.',
    )
    def post(self, request):
        # Parse item data
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        data = serializer.validated_data
        dto = ItemCreateDTO(
            name=data['name'],
            sku=data['sku'],
            location_id=data['location_id'],
            type=data.get('type', 'reusable'),
            barcode=data.get('barcode'),
            category_id=data.get('category_id'),
            unit=data.get('unit', ''),
            description=data.get('description', ''),
            owner_id=data.get('owner_id'),
            quantity=data.get('quantity'),
        )
        
        try:
            # Create item first
            item = ItemService.create(
                data=dto,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            # Check if invoice file is provided
            if 'invoice_file' in request.FILES:
                invoice_file = request.FILES['invoice_file']
                invoice_amount = request.data.get('invoice_amount')
                invoice_category = request.data.get('invoice_category')
                invoice_custom_type = request.data.get('invoice_custom_type', '')
                
                # Validate invoice data
                if not invoice_amount:
                    return Response(
                        {'code': 'VALIDATION_ERROR', 'message': 'invoice_amount is required when uploading invoice.', 'details': None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if not invoice_category:
                    return Response(
                        {'code': 'VALIDATION_ERROR', 'message': 'invoice_category is required when uploading invoice.', 'details': None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    invoice_amount = float(invoice_amount)
                except (ValueError, TypeError):
                    return Response(
                        {'code': 'VALIDATION_ERROR', 'message': 'invoice_amount must be a valid number.', 'details': None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create invoice associated with item
                from apps.invoices.services import InvoiceService
                from decimal import Decimal
                
                try:
                    InvoiceService.create(
                        name=item.name,  # Use item name as invoice name (Requirement 23.3)
                        amount=Decimal(str(invoice_amount)),
                        category=invoice_category,
                        custom_type=invoice_custom_type,
                        item_id=item.id,
                        file=invoice_file,
                        filename=invoice_file.name,
                        operator=request.user,
                        ip=ip,
                        user_agent=user_agent,
                    )
                except BusinessConflictError as e:
                    # Invoice creation failed, but item was created
                    # Return item with warning
                    response_serializer = ItemSerializer(item)
                    response_data = response_serializer.data
                    response_data['invoice_warning'] = f'Item created but invoice upload failed: {e.message}'
                    return Response(response_data, status=status.HTTP_201_CREATED)
            
            response_serializer = ItemSerializer(item)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Location.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Location not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except Category.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Category not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ItemBatchDeleteView(APIView):
    """Batch delete items (hard delete)."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Item IDs to delete'},
                },
                'required': ['ids'],
            }
        },
        responses={
            204: OpenApiResponse(description='Items deleted'),
            400: OpenApiResponse(description='No IDs provided'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Items'],
        summary='Batch delete items',
        description='Permanently delete multiple items. Super Admin only.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        
        if not ids:
            return Response(
                {'code': 'NO_IDS', 'message': 'No item IDs provided.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        deleted_count = 0
        errors = []
        
        for item_id in ids:
            try:
                ItemService.delete(
                    item_id=item_id,
                    operator=request.user,
                    ip=ip,
                    user_agent=user_agent,
                )
                deleted_count += 1
            except Item.DoesNotExist:
                errors.append(f'Item {item_id} not found')
            except BusinessConflictError as e:
                errors.append(f'Item {item_id}: {e.message}')
        
        if errors and deleted_count == 0:
            return Response(
                {'code': 'DELETE_FAILED', 'message': 'Failed to delete items.', 'details': errors},
                status=status.HTTP_409_CONFLICT
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class WarehouseBatchDeleteView(APIView):
    """Batch delete warehouses (hard delete)."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Warehouse IDs to delete'},
                },
                'required': ['ids'],
            }
        },
        responses={
            204: OpenApiResponse(description='Warehouses deleted'),
            400: OpenApiResponse(description='No IDs provided'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Warehouses'],
        summary='Batch delete warehouses',
        description='Permanently delete multiple warehouses. Super Admin only.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        
        if not ids:
            return Response(
                {'code': 'NO_IDS', 'message': 'No warehouse IDs provided.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        deleted_count = 0
        errors = []
        
        for warehouse_id in ids:
            try:
                WarehouseService.delete(
                    warehouse_id=warehouse_id,
                    operator=request.user,
                    ip=ip,
                    user_agent=user_agent,
                )
                deleted_count += 1
            except Warehouse.DoesNotExist:
                errors.append(f'Warehouse {warehouse_id} not found')
            except BusinessConflictError as e:
                errors.append(f'Warehouse {warehouse_id}: {e.message}')
        
        if errors and deleted_count == 0:
            return Response(
                {'code': 'DELETE_FAILED', 'message': 'Failed to delete warehouses.', 'details': errors},
                status=status.HTTP_409_CONFLICT
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryBatchDeleteView(APIView):
    """Batch delete categories (hard delete)."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Category IDs to delete'},
                },
                'required': ['ids'],
            }
        },
        responses={
            204: OpenApiResponse(description='Categories deleted'),
            400: OpenApiResponse(description='No IDs provided'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Categories'],
        summary='Batch delete categories',
        description='Permanently delete multiple categories. Super Admin only.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        
        if not ids:
            return Response(
                {'code': 'NO_IDS', 'message': 'No category IDs provided.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        deleted_count = 0
        errors = []
        
        for category_id in ids:
            try:
                CategoryService.delete(
                    category_id=category_id,
                    operator=request.user,
                    ip=ip,
                    user_agent=user_agent,
                )
                deleted_count += 1
            except Category.DoesNotExist:
                errors.append(f'Category {category_id} not found')
            except BusinessConflictError as e:
                errors.append(f'Category {category_id}: {e.message}')
        
        if errors and deleted_count == 0:
            return Response(
                {'code': 'DELETE_FAILED', 'message': 'Failed to delete categories.', 'details': errors},
                status=status.HTTP_409_CONFLICT
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemBatchUpdateLocationView(APIView):
    """Batch update location for multiple items."""
    permission_classes = [IsItemManagerOrSuperAdmin]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'item_ids': {'type': 'array', 'items': {'type': 'integer'}},
                    'location_id': {'type': 'integer'},
                },
                'required': ['item_ids', 'location_id'],
            }
        },
        responses={
            200: OpenApiResponse(description='Items updated successfully'),
            400: OpenApiResponse(description='Invalid request'),
            404: OpenApiResponse(description='Location not found'),
            409: OpenApiResponse(description='Location inactive'),
        },
        tags=['Items'],
        summary='Batch update item locations',
        description='Move multiple items to a new location. Item Manager or Super Admin only.',
    )
    def post(self, request):
        item_ids = request.data.get('item_ids', [])
        location_id = request.data.get('location_id')
        
        if not item_ids:
            return Response(
                {'code': 'NO_ITEM_IDS', 'message': '请选择要迁移的物品', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not location_id:
            return Response(
                {'code': 'NO_LOCATION_ID', 'message': '请选择目标库位', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            updated_count = ItemService.batch_update_location(
                item_ids=item_ids,
                location_id=location_id,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response({
                'success': True,
                'updated_count': updated_count,
                'message': f'成功迁移 {updated_count} 个物品到新库位',
            }, status=status.HTTP_200_OK)
        except Location.DoesNotExist:
            return Response(
                {'code': 'LOCATION_NOT_FOUND', 'message': '目标库位不存在', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class ItemBatchUpdateOwnerView(APIView):
    """Batch update owner for multiple items."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'item_ids': {'type': 'array', 'items': {'type': 'integer'}},
                    'owner_id': {'type': 'integer'},
                },
                'required': ['item_ids', 'owner_id'],
            }
        },
        responses={
            200: OpenApiResponse(description='Items updated successfully'),
            400: OpenApiResponse(description='Invalid request'),
            404: OpenApiResponse(description='User not found'),
            409: OpenApiResponse(description='User inactive'),
        },
        tags=['Items'],
        summary='Batch update item owners',
        description='Change owner for multiple items. Super Admin only.',
    )
    def post(self, request):
        item_ids = request.data.get('item_ids', [])
        owner_id = request.data.get('owner_id')
        
        if not item_ids:
            return Response(
                {'code': 'NO_ITEM_IDS', 'message': '请选择要更改的物品', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not owner_id:
            return Response(
                {'code': 'NO_OWNER_ID', 'message': '请选择新负责人', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            updated_count = ItemService.batch_update_owner(
                item_ids=item_ids,
                owner_id=owner_id,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response({
                'success': True,
                'updated_count': updated_count,
                'message': f'成功更改 {updated_count} 个物品的负责人',
            }, status=status.HTTP_200_OK)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT if e.code == 'USER_INACTIVE' else status.HTTP_404_NOT_FOUND
            )
