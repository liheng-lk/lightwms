"""
Invite code service for LightWMS.
Handles invite code creation, validation, and usage.
"""
import secrets
import string
from typing import Optional

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.users.models import InviteCode, User, UserRole, InviteCodeStatus


class InviteCodeService:
    """
    Service for managing invite codes.
    
    Handles:
    - Creating new invite codes with unique INV-XXXXXX format
    - Validating and using invite codes during registration
    - Disabling invite codes
    """
    
    # Code format: INV-XXXXXX (6 alphanumeric characters)
    CODE_PREFIX = 'INV-'
    CODE_LENGTH = 6
    CODE_CHARS = string.ascii_uppercase + string.digits
    
    # Maximum retry attempts for generating unique code
    MAX_GENERATION_RETRIES = 10
    
    def _generate_code(self) -> str:
        """
        Generate a unique invite code in format INV-XXXXXX.
        
        Returns:
            Unique invite code string
        
        Raises:
            RuntimeError: If unable to generate unique code after max retries
        """
        for _ in range(self.MAX_GENERATION_RETRIES):
            random_part = ''.join(
                secrets.choice(self.CODE_CHARS) 
                for _ in range(self.CODE_LENGTH)
            )
            code = f"{self.CODE_PREFIX}{random_part}"
            
            # Check if code already exists
            if not InviteCode.objects.filter(code=code).exists():
                return code
        
        raise RuntimeError(
            f"Failed to generate unique invite code after {self.MAX_GENERATION_RETRIES} attempts"
        )
    
    def create(
        self,
        max_uses: int,
        default_role: str,
        created_by: User,
        expires_at: Optional['datetime'] = None,
        is_active: bool = True
    ) -> InviteCode:
        """
        Create a new invite code.
        
        Args:
            max_uses: Maximum number of times the code can be used
            default_role: Role to assign to users who register with this code
            created_by: User creating the invite code (must be Super_Admin)
            expires_at: Optional expiration datetime
            is_active: Whether the code is active (default True)
        
        Returns:
            Created InviteCode instance
        
        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate max_uses
        if max_uses < 1:
            raise ValidationError({'max_uses': 'Must be at least 1.'})
        
        # Validate default_role
        valid_roles = [choice[0] for choice in UserRole.choices]
        if default_role not in valid_roles:
            raise ValidationError({
                'default_role': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            })
        
        # Generate unique code
        code = self._generate_code()
        
        # Create invite code
        invite_code = InviteCode.objects.create(
            code=code,
            max_uses=max_uses,
            current_uses=0,
            default_role=default_role,
            expires_at=expires_at,
            is_active=is_active,
            created_by=created_by
        )
        
        return invite_code
    
    def validate_and_use(self, code: str) -> InviteCode:
        """
        Validate an invite code and increment its usage count.
        
        This method uses database transaction with select_for_update
        to ensure atomic validation and usage increment, preventing
        race conditions in concurrent registration attempts.
        
        Args:
            code: The invite code to validate and use
        
        Returns:
            The validated InviteCode instance
        
        Raises:
            ValidationError: If the code is invalid, exhausted, expired, or disabled
        """
        with transaction.atomic():
            # Lock the invite code row for update
            try:
                invite_code = InviteCode.objects.select_for_update().get(code=code)
            except InviteCode.DoesNotExist:
                raise ValidationError({
                    'invite_code': 'Invalid invite code.'
                })
            
            # Check status and raise appropriate error
            status = invite_code.status
            
            if status == InviteCodeStatus.DISABLED:
                raise ValidationError({
                    'invite_code': 'This invite code has been disabled.'
                })
            
            if status == InviteCodeStatus.EXPIRED:
                raise ValidationError({
                    'invite_code': 'This invite code has expired.'
                })
            
            if status == InviteCodeStatus.EXHAUSTED:
                raise ValidationError({
                    'invite_code': 'This invite code has reached its maximum uses.'
                })
            
            # Increment usage count
            invite_code.current_uses += 1
            invite_code.save(update_fields=['current_uses', 'updated_at'])
            
            return invite_code
    
    def disable(self, invite_code_id: int, operator: User) -> InviteCode:
        """
        Disable an invite code.
        
        Args:
            invite_code_id: ID of the invite code to disable
            operator: User performing the operation (must be Super_Admin)
        
        Returns:
            The disabled InviteCode instance
        
        Raises:
            InviteCode.DoesNotExist: If invite code not found
        """
        invite_code = InviteCode.objects.get(id=invite_code_id)
        invite_code.is_active = False
        invite_code.save(update_fields=['is_active', 'updated_at'])
        
        return invite_code
    
    def get_by_code(self, code: str) -> Optional[InviteCode]:
        """
        Get an invite code by its code string.
        
        Args:
            code: The invite code string
        
        Returns:
            InviteCode instance or None if not found
        """
        try:
            return InviteCode.objects.get(code=code)
        except InviteCode.DoesNotExist:
            return None
    
    def list_invite_codes(
        self,
        status_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ):
        """
        List invite codes with optional filtering.
        
        Args:
            status_filter: Filter by computed status (active/exhausted/expired/disabled)
            is_active: Filter by is_active field
        
        Returns:
            QuerySet of InviteCode instances
        """
        queryset = InviteCode.objects.all()
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        # Note: status_filter requires post-filtering since status is computed
        # For efficiency, we filter in Python after fetching
        if status_filter:
            # This is less efficient but necessary for computed property filtering
            # In production, consider denormalizing status or using raw SQL
            codes = list(queryset)
            codes = [c for c in codes if c.status == status_filter]
            return codes
        
        return queryset
