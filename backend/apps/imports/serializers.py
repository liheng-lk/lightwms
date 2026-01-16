"""
Serializers for import/export operations.
"""
from rest_framework import serializers


class ImportErrorSerializer(serializers.Serializer):
    """Serializer for import error details."""
    row = serializers.IntegerField()
    field = serializers.CharField()
    message = serializers.CharField()


class ImportResultSerializer(serializers.Serializer):
    """Serializer for import result."""
    success_count = serializers.IntegerField()
    update_count = serializers.IntegerField()
    create_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    errors = ImportErrorSerializer(many=True)
    total_processed = serializers.IntegerField()


class ImportRequestSerializer(serializers.Serializer):
    """Serializer for import request."""
    file = serializers.FileField(required=True)
    allow_partial = serializers.BooleanField(required=False, default=True)
    
    def validate_file(self, value):
        """Validate file extension."""
        filename = value.name.lower()
        if not filename.endswith(('.csv', '.xlsx', '.xls')):
            raise serializers.ValidationError(
                'File must be CSV or XLSX format.'
            )
        return value


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export request parameters."""
    format = serializers.ChoiceField(
        choices=['csv', 'xlsx'],
        default='csv',
        required=False
    )
    category = serializers.IntegerField(required=False, allow_null=True)
    location = serializers.IntegerField(required=False, allow_null=True)
    warehouse = serializers.IntegerField(required=False, allow_null=True)
    owner = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.ChoiceField(
        choices=['reusable', 'consumable'],
        required=False,
        allow_null=True
    )
    status = serializers.CharField(required=False, allow_null=True)
    include_inactive = serializers.BooleanField(required=False, default=False)
