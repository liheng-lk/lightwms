"""
Serializers for invoice management.
"""
from rest_framework import serializers

from .models import Invoice, InvoiceStatus


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model (read operations)."""
    
    item_name = serializers.CharField(source='item.name', read_only=True, allow_null=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'name',
            'amount',
            'category',
            'custom_type',
            'project',
            'file',
            'original_filename',
            'status',
            'status_display',
            'item',
            'item_name',
            'item_sku',
            'registered_month',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class InvoiceCreateSerializer(serializers.Serializer):
    """Serializer for creating an invoice."""
    
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    category = serializers.CharField(max_length=100)
    custom_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    project = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    item_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_amount(self, value):
        """Validate amount is positive."""
        if value < 0:
            raise serializers.ValidationError('Amount must be non-negative.')
        return value


class InvoiceUpdateSerializer(serializers.Serializer):
    """Serializer for updating an invoice."""
    
    name = serializers.CharField(max_length=200, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    category = serializers.CharField(max_length=100, required=False)
    custom_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    project = serializers.CharField(max_length=200, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=InvoiceStatus.choices, required=False)
    
    def validate_amount(self, value):
        """Validate amount is positive."""
        if value is not None and value < 0:
            raise serializers.ValidationError('Amount must be non-negative.')
        return value


class InvoiceStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating invoice status (Super Admin only)."""
    
    status = serializers.ChoiceField(choices=InvoiceStatus.choices)
