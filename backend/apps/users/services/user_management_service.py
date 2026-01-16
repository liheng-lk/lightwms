"""
User management service for LightWMS.
"""
import secrets
import string
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import check_password

from apps.audit.models import AuditLog, AuditAction, TargetType
from ..models import User, UserRole


class UserManagementService:
    """
    Service for user management operations.
    
    Provides functionality for:
    - Disabling users (with token invalidation)
    - Resetting user passwords
    - Listing users with filters
    """
    
    def disable_user(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Disable a user account.
        
        This operation:
        1. Sets is_active=False
        2. Updates tokens_invalid_before to invalidate all existing tokens
        3. Creates an audit log entry
        
        Args:
            user_id: ID of the user to disable
            operator: User performing the operation (must be Super_Admin)
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The disabled User object
            
        Raises:
            User.DoesNotExist: If user not found
            ValueError: If trying to disable self
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            
            # Prevent self-disable
            if user.id == operator.id:
                raise ValueError("Cannot disable your own account")
            
            # Store before state for audit
            before_state = {
                'is_active': user.is_active,
                'tokens_invalid_before': (
                    user.tokens_invalid_before.isoformat() 
                    if user.tokens_invalid_before else None
                ),
            }
            
            # Disable user
            user.is_active = False
            
            # Invalidate all tokens - align to second precision
            user.tokens_invalid_before = timezone.now().replace(microsecond=0)
            user.save(update_fields=['is_active', 'tokens_invalid_before', 'updated_at'])
            
            # After state for audit
            after_state = {
                'is_active': user.is_active,
                'tokens_invalid_before': user.tokens_invalid_before.isoformat(),
            }
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.DEACTIVATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={'before': before_state, 'after': after_state},
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user
    
    def reset_password(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = ''
    ) -> tuple[User, str]:
        """
        Reset a user's password to a temporary password.
        
        This operation:
        1. Generates a secure temporary password
        2. Sets must_change_password=True
        3. Invalidates all existing tokens
        4. Creates an audit log entry
        
        Args:
            user_id: ID of the user whose password to reset
            operator: User performing the operation (must be Super_Admin)
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            Tuple of (User object, temporary password)
            
        Raises:
            User.DoesNotExist: If user not found
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            
            # Store before state for audit (excluding password)
            before_state = {
                'must_change_password': user.must_change_password,
                'tokens_invalid_before': (
                    user.tokens_invalid_before.isoformat() 
                    if user.tokens_invalid_before else None
                ),
            }
            
            # Generate temporary password
            temp_password = self._generate_temp_password()
            
            # Update user
            user.set_password(temp_password)
            user.must_change_password = True
            user.tokens_invalid_before = timezone.now().replace(microsecond=0)
            user.save(update_fields=[
                'password', 
                'must_change_password', 
                'tokens_invalid_before',
                'updated_at'
            ])
            
            # After state for audit
            after_state = {
                'must_change_password': user.must_change_password,
                'tokens_invalid_before': user.tokens_invalid_before.isoformat(),
                'password_reset': True,  # Indicate password was reset without exposing it
            }
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={'before': before_state, 'after': after_state},
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user, temp_password
    
    def list_users(
        self,
        role: str = None,
        is_active: bool = None,
        date_from=None,
        date_to=None,
    ):
        """
        List users with optional filters.
        
        Args:
            role: Filter by user role
            is_active: Filter by active status
            date_from: Filter by created_at >= date_from
            date_to: Filter by created_at <= date_to
            
        Returns:
            QuerySet of User objects
        """
        queryset = User.objects.all().order_by('-created_at', '-id')
        
        if role is not None:
            queryset = queryset.filter(role=role)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if date_from is not None:
            queryset = queryset.filter(created_at__gte=date_from)
        
        if date_to is not None:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset
    
    def _generate_temp_password(self, length: int = 12) -> str:
        """
        Generate a secure temporary password.
        
        Args:
            length: Password length (default 12)
            
        Returns:
            Random password string
        """
        # Use a mix of letters, digits, and safe special characters
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        
        # Ensure at least one of each type
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice('!@#$%^&*'),
        ]
        
        # Fill the rest randomly
        password.extend(secrets.choice(alphabet) for _ in range(length - 4))
        
        # Shuffle to avoid predictable positions
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        
        return ''.join(password_list)

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        operator: User,
        phone: str = None,
        email: str = None,
        department: str = None,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Create a new user (Super_Admin only).
        
        Args:
            username: Username for the new user
            password: Password for the new user
            role: User role
            operator: User performing the operation (must be Super_Admin)
            phone: Optional phone number
            email: Optional email
            department: Optional department
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The created User object
            
        Raises:
            ValueError: If username already exists
        """
        with transaction.atomic():
            # Check if username exists
            if User.objects.filter(username=username).exists():
                raise ValueError("用户名已存在")
            
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role,
                phone=phone if phone else None,
                email=email or '',
                department=department or '',
                is_active=True,
                must_change_password=False,
            )
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.CREATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={
                    'after': {
                        'username': user.username,
                        'role': user.role,
                        'is_active': user.is_active,
                    }
                },
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user

    def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Change user's own password.
        
        Args:
            user: User changing their password
            old_password: Current password
            new_password: New password
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The updated User object
            
        Raises:
            ValueError: If old password is incorrect
        """
        with transaction.atomic():
            # Verify old password
            if not check_password(old_password, user.password):
                raise ValueError("当前密码不正确")
            
            # Update password
            user.set_password(new_password)
            user.must_change_password = False
            user.save(update_fields=['password', 'must_change_password', 'updated_at'])
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={
                    'after': {
                        'password_changed': True,
                        'must_change_password': False,
                    }
                },
                operator=user,
                operator_role=user.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user

    def admin_set_password(
        self,
        user_id: int,
        new_password: str,
        operator: User,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Admin sets a user's password directly (Super_Admin only).
        
        Args:
            user_id: ID of the user whose password to set
            new_password: New password
            operator: User performing the operation (must be Super_Admin)
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The updated User object
            
        Raises:
            User.DoesNotExist: If user not found
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            
            # Update password
            user.set_password(new_password)
            user.must_change_password = False
            user.save(update_fields=['password', 'must_change_password', 'updated_at'])
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={
                    'after': {
                        'password_set_by_admin': True,
                        'must_change_password': False,
                    }
                },
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user

    def enable_user(
        self,
        user_id: int,
        operator: User,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Enable a disabled user account.
        
        Args:
            user_id: ID of the user to enable
            operator: User performing the operation (must be Super_Admin)
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The enabled User object
            
        Raises:
            User.DoesNotExist: If user not found
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            
            # Store before state for audit
            before_state = {
                'is_active': user.is_active,
            }
            
            # Enable user
            user.is_active = True
            user.save(update_fields=['is_active', 'updated_at'])
            
            # After state for audit
            after_state = {
                'is_active': user.is_active,
            }
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={'before': before_state, 'after': after_state},
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user

    def update_user_role(
        self,
        user_id: int,
        new_role: str,
        operator: User,
        ip: str = '',
        user_agent: str = ''
    ) -> User:
        """
        Update a user's role.
        
        Args:
            user_id: ID of the user whose role to update
            new_role: New role to assign
            operator: User performing the operation (must be Super_Admin)
            ip: Client IP address for audit
            user_agent: Client user agent for audit
            
        Returns:
            The updated User object
            
        Raises:
            User.DoesNotExist: If user not found
            ValueError: If trying to change own role
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            
            # Prevent changing own role
            if user.id == operator.id:
                raise ValueError("不能修改自己的角色")
            
            # Store before state for audit
            before_state = {
                'role': user.role,
            }
            
            # Update role
            user.role = new_role
            user.save(update_fields=['role', 'updated_at'])
            
            # After state for audit
            after_state = {
                'role': user.role,
            }
            
            # Create audit log
            AuditLog.objects.create(
                action=AuditAction.UPDATE,
                target_type=TargetType.USER,
                target_id=user.id,
                diff={'before': before_state, 'after': after_state},
                operator=operator,
                operator_role=operator.role,
                ip=ip,
                user_agent=user_agent,
            )
            
            return user
