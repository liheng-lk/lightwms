"""
Serializers for system settings.
"""
from rest_framework import serializers


class SystemSettingsSerializer(serializers.Serializer):
    """Serializer for system settings response."""
    logo_url = serializers.CharField(allow_null=True, allow_blank=True)


class SystemSettingsUpdateSerializer(serializers.Serializer):
    """Serializer for updating system settings."""
    logo_url = serializers.CharField(required=False, allow_blank=True)


class LogoUploadSerializer(serializers.Serializer):
    """Serializer for logo upload."""
    logo = serializers.FileField()
