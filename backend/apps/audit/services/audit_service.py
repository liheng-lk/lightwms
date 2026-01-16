"""
Audit service for logging data modifications and querying audit history.
"""
from typing import Any, Dict, List, Optional
from django.db.models import QuerySet
from django.utils import timezone

from apps.audit.models import AuditLog, AuditAction, TargetType, LoginLog


class AuditService:
    """
    Service for creating and querying audit logs.
    
    Provides methods for:
    - Creating audit log entries for data modifications
    - Querying resource history
    - Querying user activity
    """
    
    # Fields that should never appear in audit diffs
    SENSITIVE_FIELDS = {
        'password',
        'password_hash',
        'token',
        'refresh_token',
        'wechat_session',
    }
    
    @classmethod
    def log(
        cls,
        action: str,
        target_type: str,
        target_id: int,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        operator=None,
        operator_role: str = '',
        ip: Optional[str] = None,
        user_agent: str = '',
        request=None,
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            action: The action performed (from AuditAction choices)
            target_type: The type of resource affected (from TargetType choices)
            target_id: The ID of the affected resource
            before: State before the change (optional)
            after: State after the change (optional)
            operator: The user who performed the action
            operator_role: The role of the operator at the time of action
            ip: Client IP address (extracted from request if not provided)
            user_agent: Client user agent (extracted from request if not provided)
            request: Django request object (used to extract IP/UA if not provided)
        
        Returns:
            The created AuditLog instance
        """
        # Extract IP and user_agent from request if not provided
        if request is not None:
            if ip is None:
                ip = getattr(request, 'client_ip', None) or cls._get_client_ip(request)
            if not user_agent:
                user_agent = getattr(request, 'user_agent', '') or request.META.get('HTTP_USER_AGENT', '')
        
        # Filter sensitive fields from before/after
        filtered_before = cls._filter_sensitive_fields(before) if before else None
        filtered_after = cls._filter_sensitive_fields(after) if after else None
        
        # Build diff
        diff = {}
        if filtered_before is not None:
            diff['before'] = filtered_before
        if filtered_after is not None:
            diff['after'] = filtered_after
        
        # Get operator role if not provided
        if not operator_role and operator:
            operator_role = getattr(operator, 'role', '')
        
        # Create the audit log entry
        audit_log = AuditLog.objects.create(
            action=action,
            target_type=target_type,
            target_id=target_id,
            diff=diff,
            operator=operator,
            operator_role=operator_role,
            ip=ip,
            user_agent=user_agent,
        )
        
        return audit_log
    
    @classmethod
    def log_login(
        cls,
        username: str,
        user=None,
        success: bool = True,
        ip: str = '',
        user_agent: str = '',
        request=None,
    ) -> LoginLog:
        """
        Create a login log entry.
        
        Args:
            username: The username attempted
            user: The user object (if login was successful or user exists)
            success: Whether the login was successful
            ip: Client IP address
            user_agent: Client user agent
            request: Django request object (used to extract IP/UA if not provided)
        
        Returns:
            The created LoginLog instance
        """
        # Extract IP and user_agent from request if not provided
        if request is not None:
            if not ip:
                ip = getattr(request, 'client_ip', None) or cls._get_client_ip(request)
            if not user_agent:
                user_agent = getattr(request, 'user_agent', '') or request.META.get('HTTP_USER_AGENT', '')
        
        return LoginLog.objects.create(
            username_attempted=username,
            user=user,
            success=success,
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    def get_resource_history(
        cls,
        target_type: str,
        target_id: int,
        action: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> QuerySet:
        """
        Get audit history for a specific resource.
        
        Args:
            target_type: The type of resource (from TargetType choices)
            target_id: The ID of the resource
            action: Filter by specific action (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
        
        Returns:
            QuerySet of AuditLog entries for the resource
        """
        qs = AuditLog.objects.filter(
            target_type=target_type,
            target_id=target_id,
        )
        
        if action:
            qs = qs.filter(action=action)
        
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        
        return qs.order_by('-created_at')
    
    @classmethod
    def get_user_activity(
        cls,
        user_id: int,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> QuerySet:
        """
        Get audit history for a specific user's actions.
        
        Args:
            user_id: The ID of the user
            action: Filter by specific action (optional)
            target_type: Filter by target type (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
        
        Returns:
            QuerySet of AuditLog entries for the user's actions
        """
        qs = AuditLog.objects.filter(operator_id=user_id)
        
        if action:
            qs = qs.filter(action=action)
        
        if target_type:
            qs = qs.filter(target_type=target_type)
        
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        
        return qs.order_by('-created_at')
    
    @classmethod
    def _filter_sensitive_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from a dictionary.
        
        Args:
            data: Dictionary to filter
        
        Returns:
            Dictionary with sensitive fields removed
        """
        if not data:
            return data
        
        return {
            key: value
            for key, value in data.items()
            if key.lower() not in cls.SENSITIVE_FIELDS
        }
    
    @classmethod
    def _get_client_ip(cls, request) -> str:
        """
        Extract client IP from request.
        Handles X-Forwarded-For and X-Real-IP headers.
        
        Args:
            request: Django request object
        
        Returns:
            Client IP address string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        
        return request.META.get('REMOTE_ADDR', '')
