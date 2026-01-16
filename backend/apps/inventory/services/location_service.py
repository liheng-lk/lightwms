"""
Location service for LightWMS.

Handles location CRUD operations with audit logging and tree structure management.
"""
from typing import Optional, List, Dict, Any
from django.db import transaction

from apps.inventory.models import Location, Warehouse
from apps.audit.models import AuditLog, AuditAction, TargetType
from core.exceptions import BusinessConflictError


# Error codes for location operations
WAREHOUSE_INACTIVE = 'WAREHOUSE_INACTIVE'
PARENT_DIFFERENT_WAREHOUSE = 'PARENT_DIFFERENT_WAREHOUSE'
PARENT_INACTIVE = 'PARENT_INACTIVE'
LOCATION_HAS_CHILDREN = 'LOCATION_HAS_CHILDREN'
LOCATION_HAS_ITEMS = 'LOCATION_HAS_ITEMS'


class LocationService:
    """
    Service class for location operations.
    
    Locations form a hierarchical tree structure within warehouses.
    All operations that modify data create audit log entries.
    Locations use soft delete (is_active=False) instead of hard delete.
    
    Constraints:
    - Parent location must belong to the same warehouse
    - Cannot create locations under inactive warehouses
    - Cannot deactivate locations with active children or any items
    """
    
    @classmethod
    def _get_audit_data(cls, location: Location) -> dict:
        """Extract audit-safe data from location."""
        return {
            'warehouse_id': location.warehouse_id,
            'parent_id': location.parent_id,
            'code': location.code,
            'name': location.name,
            'owner_id': location.owner_id,
            'is_active': location.is_active,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        location: Location,
        before: Optional[dict],
        after: Optional[dict],
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry for location operations."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.LOCATION,
            target_id=location.id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        warehouse_id: int,
        code: str,
        name: str,
        owner_id: int,
        parent_id: Optional[int] = None,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Location:
        """
        Create a new location.
        
        Args:
            warehouse_id: ID of parent warehouse
            code: Location code (unique within warehouse)
            name: Human-readable name
            owner_id: ID of the location owner/manager (required)
            parent_id: Optional parent location ID
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Location instance
            
        Raises:
            BusinessConflictError: If warehouse is inactive or parent is in different warehouse
            Warehouse.DoesNotExist: If warehouse not found
            Location.DoesNotExist: If parent location not found
            IntegrityError: If code already exists in warehouse
        """
        # Validate warehouse is active
        warehouse = Warehouse.objects.get(id=warehouse_id)
        if not warehouse.is_active:
            raise BusinessConflictError(
                code=WAREHOUSE_INACTIVE,
                message='Cannot create location in inactive warehouse.',
                details={'warehouse_id': warehouse_id}
            )
        
        # Validate parent location if specified
        parent = None
        if parent_id:
            parent = Location.objects.get(id=parent_id)
            
            # Parent must be in the same warehouse
            if parent.warehouse_id != warehouse_id:
                raise BusinessConflictError(
                    code=PARENT_DIFFERENT_WAREHOUSE,
                    message='Parent location must be in the same warehouse.',
                    details={
                        'parent_warehouse_id': parent.warehouse_id,
                        'target_warehouse_id': warehouse_id
                    }
                )
            
            # Parent should be active (warning, not blocking)
            # We allow creating under inactive parent for flexibility
        
        location = Location.objects.create(
            warehouse=warehouse,
            parent=parent,
            code=code,
            name=name,
            owner_id=owner_id,
            is_active=True,
        )
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.CREATE,
            location=location,
            before=None,
            after=cls._get_audit_data(location),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return location
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        location_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = '',
        **kwargs
    ) -> Location:
        """
        Update a location.
        
        Args:
            location_id: ID of location to update
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            **kwargs: Fields to update (name only, code/warehouse/parent cannot be changed)
            
        Returns:
            Updated Location instance
            
        Raises:
            Location.DoesNotExist: If location not found
        """
        location = Location.objects.select_for_update().get(id=location_id)
        before = cls._get_audit_data(location)
        
        # Update allowed fields (code, name, owner can be changed)
        # warehouse, parent are immutable after creation
        allowed_fields = {'code', 'name', 'owner_id'}
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(location, field, value)
        
        location.save()
        
        after = cls._get_audit_data(location)
        
        # Only create audit log if something changed
        if before != after:
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                location=location,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
        
        return location
    
    @classmethod
    @transaction.atomic
    def deactivate(
        cls,
        location_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Location:
        """
        Deactivate a location (soft delete).
        
        Cannot deactivate if:
        - Location has active child locations
        - Location has any items (active or inactive)
        
        Args:
            location_id: ID of location to deactivate
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Deactivated Location instance
            
        Raises:
            Location.DoesNotExist: If location not found
            BusinessConflictError: If location has children or items
        """
        location = Location.objects.select_for_update().get(id=location_id)
        
        if not location.is_active:
            # Already deactivated, no-op
            return location
        
        # Check for active children
        active_children_count = location.children.filter(is_active=True).count()
        if active_children_count > 0:
            raise BusinessConflictError(
                code=LOCATION_HAS_CHILDREN,
                message='Cannot deactivate location with active child locations.',
                details={'active_children_count': active_children_count}
            )
        
        # Check for any items (active or inactive)
        # Note: Item model will be added in Task 9, so we check if the relation exists
        if hasattr(location, 'items'):
            items_count = location.items.count()
            if items_count > 0:
                raise BusinessConflictError(
                    code=LOCATION_HAS_ITEMS,
                    message='Cannot deactivate location with items.',
                    details={'items_count': items_count}
                )
        
        before = cls._get_audit_data(location)
        
        location.is_active = False
        location.save(update_fields=['is_active', 'updated_at'])
        
        after = cls._get_audit_data(location)
        
        cls._create_audit_log(
            action=AuditAction.DEACTIVATE,
            location=location,
            before=before,
            after=after,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return location
    
    @classmethod
    def get_by_id(cls, location_id: int) -> Location:
        """
        Get a location by ID.
        
        Args:
            location_id: ID of location
            
        Returns:
            Location instance
            
        Raises:
            Location.DoesNotExist: If not found
        """
        return Location.objects.select_related('warehouse', 'parent').get(id=location_id)
    
    @classmethod
    def get_tree(
        cls,
        warehouse_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get location tree for a warehouse or all warehouses.
        
        Returns a hierarchical tree structure with deterministic ordering
        (code asc, id asc).
        
        Args:
            warehouse_id: ID of warehouse (optional, if None returns all locations)
            include_inactive: Whether to include inactive locations
            
        Returns:
            List of root location nodes, each with nested 'children' list
            
        Example output:
            [
                {
                    'id': 1,
                    'code': 'A',
                    'name': 'Zone A',
                    'is_active': True,
                    'children': [
                        {
                            'id': 2,
                            'code': 'A1',
                            'name': 'Shelf A1',
                            'is_active': True,
                            'children': []
                        }
                    ]
                }
            ]
        """
        # Build queryset with filters
        queryset = Location.objects.select_related('owner').all()
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        # Order by warehouse, code, then id for deterministic ordering
        queryset = queryset.order_by('warehouse__code', 'code', 'id')
        
        # Fetch all locations and build tree in memory
        locations = list(queryset)
        
        # Build lookup maps
        location_map = {loc.id: loc for loc in locations}
        children_map: Dict[Optional[int], List[Location]] = {None: []}
        
        for loc in locations:
            parent_id = loc.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(loc)
        
        def build_node(location: Location) -> Dict[str, Any]:
            """Build a tree node for a location."""
            children = children_map.get(location.id, [])
            return {
                'id': location.id,
                'code': location.code,
                'name': location.name,
                'is_active': location.is_active,
                'warehouse_id': location.warehouse_id,
                'parent_id': location.parent_id,
                'owner_id': location.owner_id,
                'owner_name': location.owner.username if location.owner else None,
                'children': [build_node(child) for child in children]
            }
        
        # Build tree from root nodes (parent_id is None)
        root_locations = children_map.get(None, [])
        return [build_node(loc) for loc in root_locations]
    
    @classmethod
    def list_by_warehouse(
        cls,
        warehouse_id: int,
        include_inactive: bool = False
    ):
        """
        Get flat list of locations for a warehouse.
        
        Args:
            warehouse_id: ID of warehouse
            include_inactive: Whether to include inactive locations
            
        Returns:
            QuerySet of locations
        """
        queryset = Location.objects.filter(warehouse_id=warehouse_id)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('warehouse', 'parent').order_by('code', 'id')
