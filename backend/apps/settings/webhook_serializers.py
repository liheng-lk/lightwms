"""
Webhook serializers for LightWMS.
"""
from rest_framework import serializers

from .webhook_models import WebhookEvent


VALID_EVENTS = [choice[0] for choice in WebhookEvent.choices]


class WebhookEndpointSerializer(serializers.Serializer):
    """Serializer for webhook endpoint responses."""
    id = serializers.IntegerField(read_only=True)
    url = serializers.URLField()
    name = serializers.CharField(allow_blank=True, default='')
    secret = serializers.CharField(allow_blank=True, default='')
    events = serializers.ListField(child=serializers.CharField())
    is_active = serializers.BooleanField()
    created_by = serializers.IntegerField(source='created_by_id', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class WebhookEndpointCreateSerializer(serializers.Serializer):
    """Serializer for creating webhook endpoints."""
    url = serializers.URLField(max_length=2048)
    name = serializers.CharField(required=False, allow_blank=True, max_length=200, default='')
    secret = serializers.CharField(required=False, allow_blank=True, max_length=255, default='')
    events = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
    )
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_events(self, value):
        invalid = [e for e in value if e not in VALID_EVENTS]
        if invalid:
            raise serializers.ValidationError(
                f'无效的事件类型: {", ".join(invalid)}。'
                f'可选值: {", ".join(VALID_EVENTS)}'
            )
        return value


class WebhookEndpointUpdateSerializer(serializers.Serializer):
    """Serializer for updating webhook endpoints."""
    url = serializers.URLField(required=False, max_length=2048)
    name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    secret = serializers.CharField(required=False, allow_blank=True, max_length=255)
    events = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        min_length=1,
    )
    is_active = serializers.BooleanField(required=False)

    def validate_events(self, value):
        invalid = [e for e in value if e not in VALID_EVENTS]
        if invalid:
            raise serializers.ValidationError(
                f'无效的事件类型: {", ".join(invalid)}。'
                f'可选值: {", ".join(VALID_EVENTS)}'
            )
        return value
