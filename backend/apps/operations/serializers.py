"""
Serializers for operations management.
"""
from rest_framework import serializers

from .models import BorrowRecord, BorrowStatus, TakeRecord, ReplenishRecord


class BorrowRecordSerializer(serializers.ModelSerializer):
    """Serializer for BorrowRecord model (read operations)."""
    
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    borrower_username = serializers.CharField(source='borrower.username', read_only=True)
    borrower_name = serializers.CharField(source='borrower.username', read_only=True)
    borrower_phone = serializers.CharField(source='borrower.phone', read_only=True, allow_null=True)
    borrower_email = serializers.CharField(source='borrower.email', read_only=True, allow_null=True)
    borrower_department = serializers.CharField(source='borrower.department', read_only=True)
    operator_username = serializers.CharField(source='operator.username', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    computed_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = BorrowRecord
        fields = [
            'id', 'item', 'item_sku', 'item_name', 'borrower',
            'borrower_username', 'borrower_name', 'borrower_phone',
            'borrower_email', 'borrower_department', 'operator',
            'operator_username', 'operator_name', 'quantity',
            'expected_return_date', 'actual_return_datetime', 'notes',
            'return_notes', 'condition', 'status', 'computed_status',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class BorrowRequestSerializer(serializers.Serializer):
    """Serializer for borrow request."""
    borrower = serializers.IntegerField(source='borrower_id')
    quantity = serializers.IntegerField(min_value=1, default=1)
    expected_return_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_expected_return_date(self, value):
        from django.utils import timezone
        today = timezone.localdate()
        if value < today:
            raise serializers.ValidationError('Expected return date must be today or in the future.')
        return value


class ReturnRequestSerializer(serializers.Serializer):
    """Serializer for return request.

    `borrow_record_id` is optional for backward compatibility. It becomes
    required only when the caller has more than one eligible active record.
    """
    borrow_record_id = serializers.IntegerField(required=False, min_value=1)
    return_notes = serializers.CharField(required=False, allow_blank=True, default='')
    condition = serializers.CharField(required=False, allow_blank=True, default='')


class RecentBorrowerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    department = serializers.CharField()


class TakeRecordSerializer(serializers.ModelSerializer):
    """Serializer for TakeRecord model (read operations)."""
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    taker_username = serializers.CharField(source='taker.username', read_only=True)
    taker_phone = serializers.CharField(source='taker.phone', read_only=True, allow_null=True)
    taker_email = serializers.CharField(source='taker.email', read_only=True, allow_null=True)
    taker_department = serializers.CharField(source='taker.department', read_only=True)
    operator_username = serializers.CharField(source='operator.username', read_only=True)
    
    class Meta:
        model = TakeRecord
        fields = [
            'id', 'item', 'item_sku', 'item_name', 'taker', 'taker_username',
            'taker_phone', 'taker_email', 'taker_department', 'operator',
            'operator_username', 'quantity', 'notes', 'created_at',
        ]
        read_only_fields = fields


class TakeRequestSerializer(serializers.Serializer):
    """Serializer for take request."""
    taker = serializers.IntegerField(source='taker_id')
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ReplenishRecordSerializer(serializers.ModelSerializer):
    """Serializer for ReplenishRecord model (read operations)."""
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    operator_username = serializers.CharField(source='operator.username', read_only=True)
    
    class Meta:
        model = ReplenishRecord
        fields = [
            'id', 'item', 'item_sku', 'item_name', 'operator',
            'operator_username', 'quantity', 'notes', 'created_at',
        ]
        read_only_fields = fields


class ReplenishRequestSerializer(serializers.Serializer):
    """Serializer for replenish request."""
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
