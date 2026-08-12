"""
Serializers for audit log API.
"""
from rest_framework import serializers

from .models import AuditLog, LoginLog, AuditAction, TargetType
from .sanitization import sanitize_audit_data


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for immutable AuditLog model."""

    operator_username = serializers.CharField(
        source='operator.username',
        read_only=True,
        allow_null=True
    )
    diff = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'target_type',
            'target_id',
            'diff',
            'operator',
            'operator_username',
            'operator_role',
            'ip',
            'user_agent',
            'created_at',
        ]
        read_only_fields = fields

    def get_diff(self, obj):
        # Historic rows created before central sanitization are protected at
        # the API boundary as well.
        return sanitize_audit_data(obj.diff or {})


class LoginLogSerializer(serializers.ModelSerializer):
    """Serializer for LoginLog model."""

    user_username = serializers.CharField(
        source='user.username',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = LoginLog
        fields = [
            'id',
            'username_attempted',
            'user',
            'user_username',
            'success',
            'ip',
            'user_agent',
            'created_at',
        ]
        read_only_fields = fields


class AuditLogFilterSerializer(serializers.Serializer):
    """Serializer for audit log filter parameters."""

    action = serializers.ChoiceField(
        choices=AuditAction.choices,
        required=False,
        allow_null=True
    )
    target_type = serializers.ChoiceField(
        choices=TargetType.choices,
        required=False,
        allow_null=True
    )
    operator_id = serializers.IntegerField(required=False, allow_null=True)
    date_from = serializers.DateTimeField(required=False, allow_null=True)
    date_to = serializers.DateTimeField(required=False, allow_null=True)
