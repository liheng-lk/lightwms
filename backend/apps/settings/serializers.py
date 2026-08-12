"""
Serializers for system settings.
"""
from urllib.parse import urlsplit

from rest_framework import serializers


class SystemSettingsSerializer(serializers.Serializer):
    """Serializer for system settings response."""
    logo_url = serializers.CharField(allow_null=True, allow_blank=True)


class SystemSettingsUpdateSerializer(serializers.Serializer):
    """Serializer for updating system settings."""
    logo_url = serializers.CharField(required=False, allow_blank=True, max_length=2048)

    def validate_logo_url(self, value):
        if value == '':
            return value

        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise serializers.ValidationError('Invalid logo URL.') from exc

        if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname:
            raise serializers.ValidationError('Logo URL must use http or https.')
        if parsed.username is not None or parsed.password is not None:
            raise serializers.ValidationError('Logo URL must not contain credentials.')

        # Reject control characters and whitespace that can produce ambiguous
        # browser/network parsing even if urlsplit accepted the string.
        if any(ord(char) < 0x20 or char.isspace() for char in value):
            raise serializers.ValidationError('Logo URL contains unsafe characters.')
        return value


class LogoUploadSerializer(serializers.Serializer):
    """Serializer for logo upload."""
    logo = serializers.FileField()
