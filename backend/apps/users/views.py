"""
Views for user authentication and management.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsSuperAdmin
from core.pagination import StandardPagination
from .models import InviteCode, User, UserRole
from .serializers import (
    LoginSerializer,
    TokenResponseSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    UserMeSerializer,
    InviteCodeSerializer,
    InviteCodeCreateSerializer,
    InviteCodeUpdateSerializer,
    WechatAuthorizeResponseSerializer,
    WechatCallbackSerializer,
    WechatCallbackResponseSerializer,
    RegisterSerializer,
    SimpleRegisterSerializer,
    RegisterResponseSerializer,
    UserListSerializer,
    UserDisableResponseSerializer,
    UserResetPasswordResponseSerializer,
    UserCreateSerializer,
    UserCreateResponseSerializer,
    ChangePasswordSerializer,
    AdminSetPasswordSerializer,
    UserUpdateRoleSerializer,
)
from .services import AuthService, InviteCodeService, RegistrationService, UserManagementService


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    
    Authenticate user with username and password.
    Returns access and refresh tokens on success.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
            429: OpenApiResponse(description='Rate limited'),
        },
        tags=['Authentication'],
        summary='User login',
        description='Authenticate with username and password to obtain JWT tokens.',
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        auth_service = AuthService()
        
        # Get client IP and user agent from request
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        token_pair, user = auth_service.login(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
            ip=ip,
            user_agent=user_agent
        )
        
        return Response({
            'access': token_pair.access,
            'refresh': token_pair.refresh,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    
    Logout user by blacklisting their refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description='Successfully logged out'),
            400: OpenApiResponse(description='Invalid token'),
        },
        tags=['Authentication'],
        summary='User logout',
        description='Logout by blacklisting the refresh token.',
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        auth_service = AuthService()
        success = auth_service.logout(serializer.validated_data['refresh'])
        
        if success:
            return Response({
                'message': 'Successfully logged out.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'code': 'INVALID_TOKEN',
                'message': 'Invalid or expired token.',
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)


class RefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    
    Refresh tokens using a valid refresh token.
    Implements token rotation.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RefreshTokenSerializer,
        responses={
            200: TokenResponseSerializer,
            401: OpenApiResponse(description='Invalid or expired token'),
        },
        tags=['Authentication'],
        summary='Refresh tokens',
        description='Get new access and refresh tokens using a valid refresh token.',
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        auth_service = AuthService()
        
        try:
            token_pair = auth_service.refresh(serializer.validated_data['refresh'])
            
            return Response({
                'access': token_pair.access,
                'refresh': token_pair.refresh,
            }, status=status.HTTP_200_OK)
        except (InvalidToken, TokenError) as e:
            return Response({
                'code': 'INVALID_TOKEN',
                'message': str(e),
                'details': None,
            }, status=status.HTTP_401_UNAUTHORIZED)


class UserMeView(APIView):
    """
    GET /api/v1/users/me/
    
    Get current authenticated user's information.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: UserMeSerializer,
            401: OpenApiResponse(description='Not authenticated'),
        },
        tags=['Users'],
        summary='Get current user',
        description='Get the currently authenticated user\'s information.',
    )
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Invite Code Views

class InviteCodeListCreateView(APIView):
    """
    GET /api/v1/invite-codes/
    POST /api/v1/invite-codes/
    
    List and create invite codes (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        responses={
            200: InviteCodeSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invite Codes'],
        summary='List invite codes',
        description='Get all invite codes with pagination. Super_Admin only.',
    )
    def get(self, request):
        # Get optional status filter
        status_filter = request.query_params.get('status')
        is_active = request.query_params.get('is_active')
        
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
        service = InviteCodeService()
        invite_codes = service.list_invite_codes(
            status_filter=status_filter,
            is_active=is_active
        )
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(invite_codes, request)
        
        if page is not None:
            serializer = InviteCodeSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = InviteCodeSerializer(invite_codes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=InviteCodeCreateSerializer,
        responses={
            201: InviteCodeSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invite Codes'],
        summary='Create invite code',
        description='Create a new invite code. Super_Admin only.',
    )
    def post(self, request):
        serializer = InviteCodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = InviteCodeService()
        invite_code = service.create(
            max_uses=serializer.validated_data['max_uses'],
            default_role=serializer.validated_data['default_role'],
            created_by=request.user,
            expires_at=serializer.validated_data.get('expires_at'),
            is_active=serializer.validated_data.get('is_active', True)
        )
        
        response_serializer = InviteCodeSerializer(invite_code)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class InviteCodeDetailView(APIView):
    """
    PATCH /api/v1/invite-codes/{id}/
    
    Update an invite code (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    
    def get_object(self, pk):
        try:
            return InviteCode.objects.get(pk=pk)
        except InviteCode.DoesNotExist:
            return None
    
    @extend_schema(
        request=InviteCodeUpdateSerializer,
        responses={
            200: InviteCodeSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Invite Codes'],
        summary='Update invite code',
        description='Update an invite code. Super_Admin only.',
    )
    def patch(self, request, pk):
        invite_code = self.get_object(pk)
        if not invite_code:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'Invite code not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = InviteCodeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update fields
        for field, value in serializer.validated_data.items():
            setattr(invite_code, field, value)
        invite_code.save()
        
        response_serializer = InviteCodeSerializer(invite_code)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# WeChat OAuth Views

class WechatAuthorizeView(APIView):
    """
    GET /api/v1/auth/wechat/authorize/
    
    Get WeChat OAuth authorization URL.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: WechatAuthorizeResponseSerializer,
        },
        tags=['Authentication'],
        summary='Get WeChat authorize URL',
        description='Get the WeChat OAuth authorization URL for user registration.',
    )
    def get(self, request):
        service = RegistrationService()
        redirect_uri = request.query_params.get('redirect_uri')
        authorize_url = service.initiate_wechat_oauth(redirect_uri=redirect_uri)
        
        return Response({
            'authorize_url': authorize_url
        }, status=status.HTTP_200_OK)


class WechatCallbackView(APIView):
    """
    POST /api/v1/auth/wechat/callback/
    
    Handle WeChat OAuth callback.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=WechatCallbackSerializer,
        responses={
            200: WechatCallbackResponseSerializer,
            400: OpenApiResponse(description='Invalid callback'),
        },
        tags=['Authentication'],
        summary='WeChat OAuth callback',
        description='Handle WeChat OAuth callback and create a temporary session.',
    )
    def post(self, request):
        serializer = WechatCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = RegistrationService()
        result = service.handle_wechat_callback(
            code=serializer.validated_data['code'],
            state=serializer.validated_data.get('state')
        )
        
        return Response({
            'session_id': result.session_id,
            'nickname': result.nickname,
        }, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    
    Register a new user with WeChat session and invite code.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: RegisterResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
        tags=['Authentication'],
        summary='Register new user',
        description='Register a new user with WeChat session and invite code.',
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = RegistrationService()
        user = service.register(
            wechat_session_id=serializer.validated_data['wechat_session_id'],
            invite_code=serializer.validated_data['invite_code'],
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
            phone=serializer.validated_data.get('phone'),
            email=serializer.validated_data.get('email'),
            department=serializer.validated_data.get('department'),
        )
        
        return Response({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'message': 'Registration successful.',
        }, status=status.HTTP_201_CREATED)


class SimpleRegisterView(APIView):
    """
    POST /api/v1/auth/simple-register/
    
    Register a new user with invite code only (no WeChat required).
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=SimpleRegisterSerializer,
        responses={
            201: RegisterResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
        tags=['Authentication'],
        summary='Simple register new user',
        description='Register a new user with invite code only (no WeChat required).',
    )
    def post(self, request):
        serializer = SimpleRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = RegistrationService()
        user = service.simple_register(
            invite_code=serializer.validated_data['invite_code'],
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
            phone=serializer.validated_data.get('phone'),
            email=serializer.validated_data.get('email'),
            department=serializer.validated_data.get('department'),
        )
        
        return Response({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'message': 'Registration successful.',
        }, status=status.HTTP_201_CREATED)


# User Management Views (Super_Admin only)

class UserListView(APIView):
    """
    GET /api/v1/users/
    
    List all users with optional filters (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardPagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='role',
                description='Filter by user role',
                required=False,
                type=str,
                enum=[choice[0] for choice in UserRole.choices],
            ),
            OpenApiParameter(
                name='is_active',
                description='Filter by active status',
                required=False,
                type=bool,
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
            200: UserListSerializer(many=True),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Users'],
        summary='List users',
        description='Get all users with optional filters. Super_Admin only.',
    )
    def get(self, request):
        from dateutil.parser import parse as parse_date
        
        # Get filter parameters
        role = request.query_params.get('role')
        is_active = request.query_params.get('is_active')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Parse is_active
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
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
        
        service = UserManagementService()
        users = service.list_users(
            role=role,
            is_active=is_active,
            date_from=date_from,
            date_to=date_to,
        )
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(users, request)
        
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserDisableView(APIView):
    """
    POST /api/v1/users/{id}/disable/
    
    Disable a user account (Super_Admin only).
    This also invalidates all their tokens.
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            200: UserDisableResponseSerializer,
            400: OpenApiResponse(description='Cannot disable self'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Disable user',
        description='Disable a user account and invalidate all their tokens. Super_Admin only.',
    )
    def post(self, request, pk):
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user = service.disable_user(
                user_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'message': 'User disabled successfully.',
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'User not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)
            
        except ValueError as e:
            return Response({
                'code': 'INVALID_OPERATION',
                'message': str(e),
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)


class UserResetPasswordView(APIView):
    """
    POST /api/v1/users/{id}/reset-password/
    
    Reset a user's password to a temporary password (Super_Admin only).
    The user will be required to change their password on next login.
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            200: UserResetPasswordResponseSerializer,
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Reset user password',
        description='Reset a user\'s password to a temporary password. Super_Admin only.',
    )
    def post(self, request, pk):
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user, temp_password = service.reset_password(
                user_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'temporary_password': temp_password,
                'must_change_password': user.must_change_password,
                'message': 'Password reset successfully. User must change password on next login.',
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'User not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)


class UserCreateView(APIView):
    """
    POST /api/v1/users/create/
    
    Create a new user (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: UserCreateResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Users'],
        summary='Create user',
        description='Create a new user. Super_Admin only.',
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user = service.create_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                role=serializer.validated_data['role'],
                operator=request.user,
                phone=serializer.validated_data.get('phone'),
                email=serializer.validated_data.get('email'),
                department=serializer.validated_data.get('department'),
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'message': '用户创建成功',
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'code': 'VALIDATION_ERROR',
                'message': str(e),
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    POST /api/v1/users/me/change-password/
    
    Change current user's password.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Invalid old password'),
        },
        tags=['Users'],
        summary='Change password',
        description='Change current user\'s password.',
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            service.change_password(
                user=request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password'],
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'message': '密码修改成功',
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'code': 'INVALID_PASSWORD',
                'message': str(e),
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminSetPasswordView(APIView):
    """
    POST /api/v1/users/{id}/set-password/
    
    Admin sets a user's password directly (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request=AdminSetPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password set successfully'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Set user password',
        description='Admin sets a user\'s password directly. Super_Admin only.',
    )
    def post(self, request, pk):
        serializer = AdminSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user = service.admin_set_password(
                user_id=pk,
                new_password=serializer.validated_data['new_password'],
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'message': '密码设置成功',
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'User not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)


class UserEnableView(APIView):
    """
    POST /api/v1/users/{id}/enable/
    
    Enable a disabled user account (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        responses={
            200: UserDisableResponseSerializer,
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Enable user',
        description='Enable a disabled user account. Super_Admin only.',
    )
    def post(self, request, pk):
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user = service.enable_user(
                user_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'message': '用户已启用',
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'User not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)


class UserUpdateRoleView(APIView):
    """
    POST /api/v1/users/{id}/update-role/
    
    Update a user's role (Super_Admin only).
    """
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        request=UserUpdateRoleSerializer,
        responses={
            200: UserListSerializer,
            400: OpenApiResponse(description='Cannot change own role'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='User not found'),
        },
        tags=['Users'],
        summary='Update user role',
        description='Update a user\'s role. Super_Admin only.',
    )
    def post(self, request, pk):
        serializer = UserUpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = UserManagementService()
        
        # Get client IP and user agent
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            user = service.update_user_role(
                user_id=pk,
                new_role=serializer.validated_data['role'],
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            
            return Response({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'message': '角色已更新',
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'code': 'NOT_FOUND',
                'message': 'User not found.',
                'details': None,
            }, status=status.HTTP_404_NOT_FOUND)
            
        except ValueError as e:
            return Response({
                'code': 'INVALID_OPERATION',
                'message': str(e),
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)
