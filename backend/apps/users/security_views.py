"""Security-focused authentication view wrappers."""
from rest_framework import status
from rest_framework.response import Response

from .serializers import LogoutSerializer
from .services import AuthService
from .views import LogoutView as BaseLogoutView


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
