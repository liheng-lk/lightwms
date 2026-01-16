"""
Warehouse service for LightWMS.

Handles warehouse CRUD operations with audit logging.
"""
from typing import Optional
from django.db import transaction

from apps.inventory.models import Warehouse
from apps.audit.models import AuditLog, AuditAction, TargetType


class WarehouseService:
    """
    Service class for warehouse operations.
    
    All operations that modify data create audit log entries.
    Warehouses use soft delete (is_active=False) instead of hard delete.
    """
    
    # Fields to exclude from audit diff
    AUDIT_EXCLUDE_FIELDS = {'id', 'created_at', 'updated_at'}
    
    @classmethod
    def _get_audit_data(cls, warehouse: Warehouse) -> dict:
        """Extract audit-safe data from warehouse."""
        return {
            'code': warehouse.code,
            'name': warehouse.name,
            'description': warehouse.description,
            'is_active': warehouse.is_active,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        warehouse: Warehouse,
        before: Optional[dict],
        after: Optional[dict],
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry for warehouse operations."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.WAREHOUSE,
            target_id=warehouse.id,
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
        code: str,
        name: str,
        description: str = '',
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Warehouse:
        """
        Create a new warehouse.
        
        Args:
            code: Unique warehouse code
            name: Human-readable name
            description: Optional description
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Warehouse instance
            
        Raises:
            IntegrityError: If code already exists
        """
        warehouse = Warehouse.objects.create(
            code=code,
            name=name,
            description=description,
            is_active=True,
        )
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.CREATE,
            warehouse=warehouse,
            before=None,
            after=cls._get_audit_data(warehouse),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return warehouse
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        warehouse_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = '',
        **kwargs
    ) -> Warehouse:
        """
        Update a warehouse.
        
        Args:
            warehouse_id: ID of warehouse to update
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            **kwargs: Fields to update (name, description)
            
        Returns:
            Updated Warehouse instance
            
        Raises:
            Warehouse.DoesNotExist: If warehouse not found
        """
        warehouse = Warehouse.objects.select_for_update().get(id=warehouse_id)
        before = cls._get_audit_data(warehouse)
        
        # Update allowed fields
        allowed_fields = {'name', 'description'}
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(warehouse, field, value)
        
        warehouse.save()
        
        after = cls._get_audit_data(warehouse)
        
        # Only create audit log if something changed
        if before != after:
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                warehouse=warehouse,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
        
        return warehouse
    
    @classmethod
    @transaction.atomic
    def deactivate(
        cls,
        warehouse_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Warehouse:
        """
        Deactivate a warehouse (soft delete).
        
        When a warehouse is deactivated:
        - New Locations cannot be created under it
        - New Items cannot be created under its locations
        - Existing data is preserved
        
        Note: Unlike Location/Category, warehouse deactivation is always
        allowed regardless of existing children. The children remain but
        are excluded from default queries.
        
        Args:
            warehouse_id: ID of warehouse to deactivate
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Deactivated Warehouse instance
            
        Raises:
            Warehouse.DoesNotExist: If warehouse not found
        """
        warehouse = Warehouse.objects.select_for_update().get(id=warehouse_id)
        
        if not warehouse.is_active:
            # Already deactivated, no-op
            return warehouse
        
        before = cls._get_audit_data(warehouse)
        
        warehouse.is_active = False
        warehouse.save(update_fields=['is_active', 'updated_at'])
        
        after = cls._get_audit_data(warehouse)
        
        cls._create_audit_log(
            action=AuditAction.DEACTIVATE,
            warehouse=warehouse,
            before=before,
            after=after,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return warehouse
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        warehouse_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> None:
        """
        Permanently delete a warehouse (hard delete).
        
        WARNING: This permanently removes the warehouse. Will fail if
        there are locations associated with this warehouse.
        
        Args:
            warehouse_id: ID of warehouse to delete
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Raises:
            Warehouse.DoesNotExist: If warehouse not found
            BusinessConflictError: If warehouse has locations
        """
        from core.exceptions import BusinessConflictError
        
        warehouse = Warehouse.objects.select_for_update().get(id=warehouse_id)
        
        # Check if warehouse has locations
        if warehouse.locations.exists():
            raise BusinessConflictError(
                code='HAS_CHILDREN',
                message='Cannot delete warehouse with existing locations.',
                details={'warehouse_id': warehouse_id}
            )
        
        before = cls._get_audit_data(warehouse)
        
        # Create audit log before deletion
        AuditLog.objects.create(
            action=AuditAction.DELETE,
            target_type=TargetType.WAREHOUSE,
            target_id=warehouse_id,
            diff={'before': before, 'after': None},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
        
        # Delete the warehouse
        warehouse.delete()
    
    @classmethod
    def get_by_id(cls, warehouse_id: int) -> Warehouse:
        """
        Get a warehouse by ID.
        
        Args:
            warehouse_id: ID of warehouse
            
        Returns:
            Warehouse instance
            
        Raises:
            Warehouse.DoesNotExist: If not found
        """
        return Warehouse.objects.get(id=warehouse_id)
    
    @classmethod
    def get_by_code(cls, code: str) -> Warehouse:
        """
        Get a warehouse by code.
        
        Args:
            code: Warehouse code
            
        Returns:
            Warehouse instance
            
        Raises:
            Warehouse.DoesNotExist: If not found
        """
        return Warehouse.objects.get(code=code)
    
    @classmethod
    def list_active(cls):
        """
        Get all active warehouses.
        
        Returns:
            QuerySet of active warehouses
        """
        return Warehouse.objects.filter(is_active=True).order_by('code')
    
    @classmethod
    def list_all(cls):
        """
        Get all warehouses including inactive.
        
        Returns:
            QuerySet of all warehouses
        """
        return Warehouse.objects.all().order_by('code')
