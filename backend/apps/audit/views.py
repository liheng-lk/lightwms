"""
Views for audit log API.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsItemManagerOrSuperAdmin
from core.pagination import StandardPagination
from .models import AuditLog, LoginLog, AuditAction, TargetType
from .serializers import AuditLogSerializer, LoginLogSerializer
from .services import AuditService


class AuditLogListView(APIView):
    """
    GET /api/v1/audit-logs/
    
    List all audit logs with optional filters (Admin only).
    """
    permission_classes = [IsItemManagerOrSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='action',
                description='Filter by action type',
                required=False,
                type=str,
                enum=[choice[0] for choice in AuditAction.choices],
            ),
            OpenApiParameter(
                name='target_type',
                description='Filter by target type',
                required=False,
                type=str,
                enum=[choice[0] for choice in TargetType.choices],
            ),
            OpenApiParameter(
                name='operator_id',
                description='Filter by operator user ID',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='date_from',
                description='Filter by created_at >= date_from (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='date_to',
                description='Filter by created_at <= date_to (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='page_size',
                description='Number of results per page',
                required=False,
                type=int,
            ),
        ],
        responses={
            200: AuditLogSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Audit'],
        summary='List audit logs',
        description='Get all audit logs with optional filters. Super_Admin only.',
    )
    def get(self, request):
        from dateutil.parser import parse as parse_date
        
        # Get filter parameters
        action = request.query_params.get('action')
        target_type = request.query_params.get('target_type')
        operator_id = request.query_params.get('operator_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse operator_id
        if operator_id:
            try:
                operator_id = int(operator_id)
            except (ValueError, TypeError):
                operator_id = None
        
        # Parse dates
        if date_from:
            try:
                date_from = parse_date(date_from)
            except (ValueError, TypeError):
                date_from = None
        
        if date_to:
            try:
                date_to = parse_date(date_to)
            except (ValueError, TypeError):
                date_to = None
        
        # Build queryset
        qs = AuditLog.objects.all()
        
        if action:
            qs = qs.filter(action=action)
        
        if target_type:
            qs = qs.filter(target_type=target_type)
        
        if operator_id:
            qs = qs.filter(operator_id=operator_id)
        
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        
        qs = qs.select_related('operator').order_by('-created_at')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = AuditLogSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogResourceHistoryView(APIView):
    """
    GET /api/v1/audit-logs/resource/{type}/{id}/
    
    Get audit history for a specific resource.
    """
    permission_classes = [IsItemManagerOrSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                description='Resource type',
                required=True,
                type=str,
                location=OpenApiParameter.PATH,
                enum=[choice[0] for choice in TargetType.choices],
            ),
            OpenApiParameter(
                name='id',
                description='Resource ID',
                required=True,
                type=int,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name='action',
                description='Filter by action type',
                required=False,
                type=str,
                enum=[choice[0] for choice in AuditAction.choices],
            ),
            OpenApiParameter(
                name='date_from',
                description='Filter by created_at >= date_from (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='date_to',
                description='Filter by created_at <= date_to (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='page_size',
                description='Number of results per page',
                required=False,
                type=int,
            ),
        ],
        responses={
            200: AuditLogSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Invalid resource type'),
        },
        tags=['Audit'],
        summary='Get resource audit history',
        description='Get audit history for a specific resource. Super_Admin only.',
    )
    def get(self, request, type, id):
        from dateutil.parser import parse as parse_date
        
        # Validate target_type
        valid_types = [choice[0] for choice in TargetType.choices]
        if type not in valid_types:
            return Response({
                'code': 'INVALID_TARGET_TYPE',
                'message': f'Invalid target type. Must be one of: {", ".join(valid_types)}',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get filter parameters
        action = request.query_params.get('action')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse dates
        if date_from:
            try:
                date_from = parse_date(date_from)
            except (ValueError, TypeError):
                date_from = None
        
        if date_to:
            try:
                date_to = parse_date(date_to)
            except (ValueError, TypeError):
                date_to = None
        
        # Get resource history using service
        qs = AuditService.get_resource_history(
            target_type=type,
            target_id=id,
            action=action,
            start_date=date_from,
            end_date=date_to,
        )
        
        qs = qs.select_related('operator')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = AuditLogSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogUserActivityView(APIView):
    """
    GET /api/v1/audit-logs/user/{id}/
    
    Get audit history for a specific user's actions.
    """
    permission_classes = [IsItemManagerOrSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                description='User ID',
                required=True,
                type=int,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name='action',
                description='Filter by action type',
                required=False,
                type=str,
                enum=[choice[0] for choice in AuditAction.choices],
            ),
            OpenApiParameter(
                name='target_type',
                description='Filter by target type',
                required=False,
                type=str,
                enum=[choice[0] for choice in TargetType.choices],
            ),
            OpenApiParameter(
                name='date_from',
                description='Filter by created_at >= date_from (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='date_to',
                description='Filter by created_at <= date_to (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='page_size',
                description='Number of results per page',
                required=False,
                type=int,
            ),
        ],
        responses={
            200: AuditLogSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Audit'],
        summary='Get user activity',
        description='Get audit history for a specific user\'s actions. Super_Admin only.',
    )
    def get(self, request, id):
        from dateutil.parser import parse as parse_date
        
        # Get filter parameters
        action = request.query_params.get('action')
        target_type = request.query_params.get('target_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse dates
        if date_from:
            try:
                date_from = parse_date(date_from)
            except (ValueError, TypeError):
                date_from = None
        
        if date_to:
            try:
                date_to = parse_date(date_to)
            except (ValueError, TypeError):
                date_to = None
        
        # Get user activity using service
        qs = AuditService.get_user_activity(
            user_id=id,
            action=action,
            target_type=target_type,
            start_date=date_from,
            end_date=date_to,
        )
        
        qs = qs.select_related('operator')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = AuditLogSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LoginLogListView(APIView):
    """
    GET /api/v1/login-logs/
    
    List all login logs with optional filters (Admin only).
    """
    permission_classes = [IsItemManagerOrSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='user_id',
                description='Filter by user ID',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='success',
                description='Filter by success status',
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name='ip',
                description='Filter by IP address',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='date_from',
                description='Filter by created_at >= date_from (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='date_to',
                description='Filter by created_at <= date_to (ISO format)',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name='page_size',
                description='Number of results per page',
                required=False,
                type=int,
            ),
        ],
        responses={
            200: LoginLogSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Audit'],
        summary='List login logs',
        description='Get all login logs with optional filters. Super_Admin only.',
    )
    def get(self, request):
        from dateutil.parser import parse as parse_date
        
        # Get filter parameters
        user_id = request.query_params.get('user_id')
        success = request.query_params.get('success')
        ip = request.query_params.get('ip')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse user_id
        if user_id:
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                user_id = None
        
        # Parse success
        if success is not None:
            success = success.lower() == 'true'
        
        # Parse dates
        if date_from:
            try:
                date_from = parse_date(date_from)
            except (ValueError, TypeError):
                date_from = None
        
        if date_to:
            try:
                date_to = parse_date(date_to)
            except (ValueError, TypeError):
                date_to = None
        
        # Build queryset
        qs = LoginLog.objects.all()
        
        if user_id:
            qs = qs.filter(user_id=user_id)
        
        if success is not None:
            qs = qs.filter(success=success)
        
        if ip:
            qs = qs.filter(ip=ip)
        
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        
        qs = qs.select_related('user').order_by('-created_at')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            serializer = LoginLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = LoginLogSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
