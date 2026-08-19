"""Super-admin endpoint for safe user deletion."""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSuperAdmin
from .models import User
from .services.user_deletion_service import UserDeletionService


class UserDeleteView(APIView):
    """DELETE /api/v1/users/{id}/ (Super Admin only)."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        responses={
            204: OpenApiResponse(description='User account deleted safely'),
            400: OpenApiResponse(description='Cannot delete current user'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Delete user',
        description=(
            'Delete a user account without removing inventory, invoice or operation history. '
            'The account is disabled and hidden from user management while historical attribution is retained.'
        ),
    )
    def delete(self, request, pk):
        service = UserDeletionService()
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        try:
            service.delete_user(
                user_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'User not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {'code': 'INVALID_OPERATION', 'message': str(exc), 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
