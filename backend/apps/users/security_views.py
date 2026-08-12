"""Security-focused authentication and invite-code view wrappers."""
from rest_framework import status
from rest_framework.response import Response

from .serializers import (
    InviteCodeSerializer,
    InviteCodeUpdateSerializer,
    LogoutSerializer,
)
from .services import AuthService
from .views import (
    InviteCodeDetailView as BaseInviteCodeDetailView,
    LogoutView as BaseLogoutView,
)


class LogoutView(BaseLogoutView):
    """Logout only the refresh token belonging to the authenticated user."""

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = AuthService().logout(
            serializer.validated_data['refresh'],
            expected_user=request.user,
        )
        if success:
            return Response(
                {'message': 'Successfully logged out.'},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                'code': 'INVALID_TOKEN',
                'message': 'Invalid or expired token.',
                'details': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class InviteCodeDetailView(BaseInviteCodeDetailView):
    """Validate mutable invite-code limits before hitting DB constraints."""

    def patch(self, request, pk):
        invite_code = self.get_object(pk)
        if not invite_code:
            return Response(
                {
                    'code': 'NOT_FOUND',
                    'message': 'Invite code not found.',
                    'details': None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = InviteCodeUpdateSerializer(
            invite_code,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(invite_code, field, value)
        invite_code.save()

        return Response(
            InviteCodeSerializer(invite_code).data,
            status=status.HTTP_200_OK,
        )
