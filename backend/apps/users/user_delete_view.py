"""Super-admin endpoint for history-safe user deletion."""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSuperAdmin
from .models import User
from .services.user_deletion_service import UserDeletionConflict, UserDeletionService


class UserDeleteView(APIView):
    """DELETE /api/v1/users/{id}/ (Super Admin only)."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        responses={
            204: OpenApiResponse(description='User removed from active user management'),
            400: OpenApiResponse(description='Cannot delete current user'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Delete user',
        description=(
            'Remove a user account. Super Admin only. Unreferenced accounts are '
            'deleted permanently; accounts referenced by inventory or business '
            'history are archived and disabled so historical records remain intact.'
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
        except UserDeletionConflict as exc:
            # Kept for compatibility with older service implementations.
            return Response(
                {
                    'code': 'USER_IN_USE',
                    'message': str(exc),
                    'details': {'protected_models': exc.protected_models},
                },
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError as exc:
            return Response(
                {'code': 'INVALID_OPERATION', 'message': str(exc), 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
