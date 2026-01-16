"""
Serializers for user authentication and management.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserRole, InviteCode, InviteCodeStatus


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to add additional claims."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['role'] = getattr(user, 'role', None)
        return token


class LoginSerializer(serializers.Serializer):
    """Serializer for login request."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh request."""
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout request."""
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read operations)."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'phone',
            'department',
            'role',
            'is_active',
            'must_change_password',
            'created_at',
            'updated_at',
            'last_login',
        ]
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    """Serializer for current user info (GET /api/v1/users/me/)."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'phone',
            'department',
            'role',
            'is_active',
            'must_change_password',
            'created_at',
            'updated_at',
            'last_login',
        ]
        read_only_fields = fields


# Invite Code Serializers

class InviteCodeSerializer(serializers.ModelSerializer):
    """Serializer for InviteCode model (read operations)."""
    
    status = serializers.CharField(read_only=True)
    remaining_uses = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(
        source='created_by.username', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = InviteCode
        fields = [
            'id',
            'code',
            'max_uses',
            'current_uses',
            'remaining_uses',
            'default_role',
            'expires_at',
            'is_active',
            'status',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'code',
            'current_uses',
            'remaining_uses',
            'status',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]


class InviteCodeCreateSerializer(serializers.Serializer):
    """Serializer for creating invite codes."""
    
    max_uses = serializers.IntegerField(min_value=1, default=1)
    default_role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.ITEM_MANAGER
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)


class InviteCodeUpdateSerializer(serializers.Serializer):
    """Serializer for updating invite codes."""
    
    max_uses = serializers.IntegerField(min_value=1, required=False)
    default_role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)


# WeChat OAuth Serializers

class WechatAuthorizeResponseSerializer(serializers.Serializer):
    """Serializer for WeChat authorize response."""
    authorize_url = serializers.URLField()


class WechatCallbackSerializer(serializers.Serializer):
    """Serializer for WeChat callback request."""
    code = serializers.CharField(max_length=200)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)


class WechatCallbackResponseSerializer(serializers.Serializer):
    """Serializer for WeChat callback response."""
    session_id = serializers.CharField()
    nickname = serializers.CharField()


# Registration Serializers

class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration with WeChat."""
    
    wechat_session_id = serializers.CharField(max_length=64)
    invite_code = serializers.CharField(max_length=20)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_username(self, value):
        """Validate username format."""
        if not value.isalnum() and '_' not in value:
            raise serializers.ValidationError(
                'Username can only contain letters, numbers, and underscores.'
            )
        return value


class SimpleRegisterSerializer(serializers.Serializer):
    """Serializer for simple user registration with invite code only (no WeChat)."""
    
    invite_code = serializers.CharField(max_length=20)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_username(self, value):
        """Validate username format."""
        # Allow letters, numbers, underscores, and Chinese characters
        import re
        if not re.match(r'^[\w\u4e00-\u9fa5]+$', value):
            raise serializers.ValidationError(
                'Username can only contain letters, numbers, underscores, and Chinese characters.'
            )
        return value


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration response."""
    
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    message = serializers.CharField()


# User Management Serializers

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list (Super_Admin only)."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'phone',
            'department',
            'role',
            'is_active',
            'must_change_password',
            'created_at',
            'updated_at',
            'last_login',
        ]
        read_only_fields = fields


class UserDisableResponseSerializer(serializers.Serializer):
    """Serializer for user disable response."""
    
    id = serializers.IntegerField()
    username = serializers.CharField()
    is_active = serializers.BooleanField()
    message = serializers.CharField()


class UserResetPasswordResponseSerializer(serializers.Serializer):
    """Serializer for password reset response."""
    
    id = serializers.IntegerField()
    username = serializers.CharField()
    temporary_password = serializers.CharField()
    must_change_password = serializers.BooleanField()
    message = serializers.CharField()


class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating a new user (Super_Admin only)."""
    
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=UserRole.choices)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_username(self, value):
        """Validate username format."""
        import re
        if not re.match(r'^[\w\u4e00-\u9fa5]+$', value):
            raise serializers.ValidationError(
                'Username can only contain letters, numbers, underscores, and Chinese characters.'
            )
        return value


class UserCreateResponseSerializer(serializers.Serializer):
    """Serializer for user creation response."""
    
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    message = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing own password."""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)


class AdminSetPasswordSerializer(serializers.Serializer):
    """Serializer for admin setting user password."""
    
    new_password = serializers.CharField(write_only=True, min_length=6)


class UserUpdateRoleSerializer(serializers.Serializer):
    """Serializer for updating user role."""
    
    role = serializers.ChoiceField(choices=UserRole.choices)
