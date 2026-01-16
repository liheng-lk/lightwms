"""
Category service for LightWMS.

Handles category CRUD operations with audit logging and tree structure management.
"""
from typing import Optional, List, Dict, Any
from django.db import transaction

from apps.inventory.models import Category
from apps.audit.models import AuditLog, AuditAction, TargetType
from core.exceptions import BusinessConflictError


# Error codes for category operations
CATEGORY_HAS_CHILDREN = 'CATEGORY_HAS_CHILDREN'
CATEGORY_HAS_ITEMS = 'CATEGORY_HAS_ITEMS'


class CategoryService:
    """
    Service class for category operations.
    
    Categories form a hierarchical tree structure.
    All operations that modify data create audit log entries.
    Categories use soft delete (is_active=False) instead of hard delete.
    
    Constraints:
    - Cannot be deactivated if it has child categories (active or inactive)
    - Cannot be deactivated if it has any items (active or inactive)
    """
    
    @classmethod
    def _get_audit_data(cls, category: Category) -> dict:
        """Extract audit-safe data from category."""
        return {
            'parent_id': category.parent_id,
            'name': category.name,
            'is_active': category.is_active,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        category: Category,
        before: Optional[dict],
        after: Optional[dict],
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry for category operations."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.CATEGORY,
            target_id=category.id,
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
        name: str,
        parent_id: Optional[int] = None,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Category:
        """
        Create a new category.
        
        Args:
            name: Category name
            parent_id: Optional parent category ID
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Category instance
            
        Raises:
            Category.DoesNotExist: If parent category not found
        """
        # Validate parent category if specified
        parent = None
        if parent_id:
            parent = Category.objects.get(id=parent_id)
        
        category = Category.objects.create(
            parent=parent,
            name=name,
            is_active=True,
        )
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.CREATE,
            category=category,
            before=None,
            after=cls._get_audit_data(category),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return category
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        category_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = '',
        **kwargs
    ) -> Category:
        """
        Update a category.
        
        Args:
            category_id: ID of category to update
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            **kwargs: Fields to update (name only, parent cannot be changed)
            
        Returns:
            Updated Category instance
            
        Raises:
            Category.DoesNotExist: If category not found
        """
        category = Category.objects.select_for_update().get(id=category_id)
        before = cls._get_audit_data(category)
        
        # Update allowed fields (only name can be changed)
        # parent is immutable after creation
        allowed_fields = {'name'}
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(category, field, value)
        
        category.save()
        
        after = cls._get_audit_data(category)
        
        # Only create audit log if something changed
        if before != after:
            cls._create_audit_log(
                action=AuditAction.UPDATE,
                category=category,
                before=before,
                after=after,
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
        
        return category
    
    @classmethod
    @transaction.atomic
    def deactivate(
        cls,
        category_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Category:
        """
        Deactivate a category (soft delete).
        
        Cannot deactivate if:
        - Category has child categories (active or inactive)
        - Category has any items (active or inactive)
        
        Args:
            category_id: ID of category to deactivate
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Deactivated Category instance
            
        Raises:
            Category.DoesNotExist: If category not found
            BusinessConflictError: If category has children or items
        """
        category = Category.objects.select_for_update().get(id=category_id)
        
        if not category.is_active:
            # Already deactivated, no-op
            return category
        
        # Check for any children (active or inactive)
        children_count = category.children.count()
        if children_count > 0:
            raise BusinessConflictError(
                code=CATEGORY_HAS_CHILDREN,
                message='Cannot deactivate category with child categories.',
                details={'children_count': children_count}
            )
        
        # Check for any items (active or inactive)
        # Note: Item model will be added in Task 9, so we check if the relation exists
        if hasattr(category, 'items'):
            items_count = category.items.count()
            if items_count > 0:
                raise BusinessConflictError(
                    code=CATEGORY_HAS_ITEMS,
                    message='Cannot deactivate category with items.',
                    details={'items_count': items_count}
                )
        
        before = cls._get_audit_data(category)
        
        category.is_active = False
        category.save(update_fields=['is_active', 'updated_at'])
        
        after = cls._get_audit_data(category)
        
        cls._create_audit_log(
            action=AuditAction.DEACTIVATE,
            category=category,
            before=before,
            after=after,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return category

    @classmethod
    def get_by_id(cls, category_id: int) -> Category:
        """
        Get a category by ID.
        
        Args:
            category_id: ID of category
            
        Returns:
            Category instance
            
        Raises:
            Category.DoesNotExist: If not found
        """
        return Category.objects.select_related('parent').get(id=category_id)
    
    @classmethod
    def get_tree(
        cls,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get category tree.
        
        Returns a hierarchical tree structure with deterministic ordering
        (name asc, id asc).
        
        Args:
            include_inactive: Whether to include inactive categories
            
        Returns:
            List of root category nodes, each with nested 'children' list
            
        Example output:
            [
                {
                    'id': 1,
                    'name': 'Electronics',
                    'is_active': True,
                    'children': [
                        {
                            'id': 2,
                            'name': 'Computers',
                            'is_active': True,
                            'children': []
                        }
                    ]
                }
            ]
        """
        # Build queryset with filters
        queryset = Category.objects.all()
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        # Order by name, then id for deterministic ordering
        queryset = queryset.order_by('name', 'id')
        
        # Fetch all categories and build tree in memory
        categories = list(queryset)
        
        # Build lookup maps
        category_map = {cat.id: cat for cat in categories}
        children_map: Dict[Optional[int], List[Category]] = {None: []}
        
        for cat in categories:
            parent_id = cat.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(cat)
        
        def build_node(category: Category) -> Dict[str, Any]:
            """Build a tree node for a category."""
            children = children_map.get(category.id, [])
            return {
                'id': category.id,
                'name': category.name,
                'is_active': category.is_active,
                'parent_id': category.parent_id,
                'children': [build_node(child) for child in children]
            }
        
        # Build tree from root nodes (parent_id is None)
        root_categories = children_map.get(None, [])
        return [build_node(cat) for cat in root_categories]
    
    @classmethod
    def list_active(cls):
        """
        Get all active categories.
        
        Returns:
            QuerySet of active categories
        """
        return Category.objects.filter(is_active=True).select_related('parent').order_by('name', 'id')
    
    @classmethod
    def list_all(cls):
        """
        Get all categories including inactive.
        
        Returns:
            QuerySet of all categories
        """
        return Category.objects.all().select_related('parent').order_by('name', 'id')

    @classmethod
    @transaction.atomic
    def delete(
        cls,
        category_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> None:
        """
        Permanently delete a category (hard delete).
        
        Cannot delete if:
        - Category has child categories
        - Category has any items
        
        Args:
            category_id: ID of category to delete
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Raises:
            Category.DoesNotExist: If category not found
            BusinessConflictError: If category has children or items
        """
        category = Category.objects.select_for_update().get(id=category_id)
        
        # Check for any children
        children_count = category.children.count()
        if children_count > 0:
            raise BusinessConflictError(
                code=CATEGORY_HAS_CHILDREN,
                message='Cannot delete category with child categories.',
                details={'children_count': children_count}
            )
        
        # Check for any items
        if hasattr(category, 'items'):
            items_count = category.items.count()
            if items_count > 0:
                raise BusinessConflictError(
                    code=CATEGORY_HAS_ITEMS,
                    message='Cannot delete category with items.',
                    details={'items_count': items_count}
                )
        
        before = cls._get_audit_data(category)
        category_id_for_log = category.id
        
        # Delete the category
        category.delete()
        
        # Create audit log for deletion
        AuditLog.objects.create(
            action=AuditAction.DELETE,
            target_type=TargetType.CATEGORY,
            target_id=category_id_for_log,
            diff={'before': before, 'after': None},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
