"""
Views for system settings.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsSuperAdmin
from .services import SystemSettingsService
from .serializers import (
    SystemSettingsSerializer,
    SystemSettingsUpdateSerializer,
    LogoUploadSerializer,
)


class SystemSettingsView(APIView):
    """Get and update system settings."""
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsSuperAdmin()]
        # Allow public access to GET for logo display on login page
        return [AllowAny()]
    
    @extend_schema(
        responses={200: SystemSettingsSerializer},
        tags=['System Settings'],
        summary='Get system settings',
        description='Get all system settings. Available to all authenticated users.',
    )
    def get(self, request):
        """Get all system settings."""
        settings_data = SystemSettingsService.get_all_settings()
        serializer = SystemSettingsSerializer(settings_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=SystemSettingsUpdateSerializer,
        responses={200: SystemSettingsSerializer},
        tags=['System Settings'],
        summary='Update system settings',
        description='Update system settings. Super Admin only.',
    )
    def put(self, request):
        """Update system settings."""
        serializer = SystemSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        data = serializer.validated_data
        
        # Update logo URL if provided
        if 'logo_url' in data:
            logo_url = data['logo_url']
            if logo_url:
                SystemSettingsService.set_logo_url(
                    url=logo_url,
                    operator=request.user,
                    ip=ip,
                    user_agent=user_agent,
                )
            else:
                # Clear logo if empty string
                SystemSettingsService.clear_logo(
                    operator=request.user,
                    ip=ip,
                    user_agent=user_agent,
                )
        
        # Return updated settings
        settings_data = SystemSettingsService.get_all_settings()
        response_serializer = SystemSettingsSerializer(settings_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LogoUploadView(APIView):
    """Upload system logo."""
    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        request={'multipart/form-data': LogoUploadSerializer},
        responses={
            200: SystemSettingsSerializer,
            400: OpenApiResponse(description='Invalid file'),
        },
        tags=['System Settings'],
        summary='Upload system logo',
        description='Upload a logo file. Super Admin only. Supported formats: PNG, JPG, SVG, WebP. Max size: 2MB.',
    )
    def post(self, request):
        """Upload a logo file."""
        serializer = LogoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            logo_url = SystemSettingsService.upload_logo(
                file=serializer.validated_data['logo'],
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            settings_data = SystemSettingsService.get_all_settings()
            response_serializer = SystemSettingsSerializer(settings_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {'code': 'INVALID_FILE', 'message': str(e), 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
