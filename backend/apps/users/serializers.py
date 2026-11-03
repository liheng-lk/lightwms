"""
Serializers for user authentication and management.
"""
import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserRole, InviteCode


_USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_\u4e00-\u9fff]+$')


def validate_account_password(value: str) -> str:
    """Apply Django's configured password validators consistently."""
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))
    return value


def validate_account_username(value: str) -> str:
    """Use one username character contract for every account creation path."""
    if not _USERNAME_PATTERN.fullmatch(value):
        raise serializers.ValidationError(
            'Username can only contain Chinese characters, English letters, numbers, and underscores.'
        )
    return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to add additional claims."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = getattr(user, 'role', None)
        return token


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'department', 'role',
            'is_active', 'must_change_password', 'created_at', 'updated_at',
            'last_login',
        ]
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'department', 'role',
            'is_active', 'must_change_password', 'created_at', 'updated_at',
            'last_login',
        ]
        read_only_fields = fields


class InviteCodeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    remaining_uses = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model = InviteCode
        fields = [
            'id', 'code', 'max_uses', 'current_uses', 'remaining_uses',
            'default_role', 'expires_at', 'is_active', 'status', 'created_by',
            'created_by_username', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'code', 'current_uses', 'remaining_uses', 'status',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
        ]


class InviteCodeCreateSerializer(serializers.Serializer):
    max_uses = serializers.IntegerField(min_value=1, default=1)
    default_role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.READ_ONLY_USER,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)


class InviteCodeUpdateSerializer(serializers.Serializer):
    max_uses = serializers.IntegerField(min_value=1, required=False)
    default_role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def validate_max_uses(self, value):
        invite_code = self.instance
        if invite_code is not None and value < invite_code.current_uses:
            raise serializers.ValidationError(
                'max_uses cannot be lower than the number of times already used.'
            )
        return value


class WechatAuthorizeResponseSerializer(serializers.Serializer):
    authorize_url = serializers.URLField()


class WechatCallbackSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=200)
    state = serializers.CharField(max_length=100)


class WechatCallbackResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    nickname = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    wechat_session_id = serializers.CharField(max_length=64)
    invite_code = serializers.CharField(max_length=20)
    username = serializers.CharField(max_length=150, validators=[validate_account_username])
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_account_password])
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SimpleRegisterSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=20)
    username = serializers.CharField(max_length=150, validators=[validate_account_username])
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_account_password])
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)


class RegisterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    message = serializers.CharField()


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'department', 'role',
            'is_active', 'must_change_password', 'created_at', 'updated_at',
            'last_login',
        ]
        read_only_fields = fields


class UserDisableResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    is_active = serializers.BooleanField()
    message = serializers.CharField()


class UserResetPasswordResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    temporary_password = serializers.CharField()
    must_change_password = serializers.BooleanField()
    message = serializers.CharField()


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=[validate_account_username])
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_account_password])
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.READ_ONLY_USER)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)


class UserCreateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    message = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, validators=[validate_account_password])


class AdminSetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8, validators=[validate_account_password])


class UserUpdateRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices)
