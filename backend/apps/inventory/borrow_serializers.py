"""Borrow-aware inventory serializers."""
from rest_framework import serializers

from apps.operations.models import BorrowStatus

from .serializers import ItemSerializer


class BorrowAwareItemSerializer(ItemSerializer):
    """Item detail serializer with all active borrow records.

    Existing single-value fields remain for compatibility. New clients should
    use `active_borrows` whenever quantity > 1 can produce concurrent borrows.
    """
    active_borrows = serializers.SerializerMethodField()

    class Meta(ItemSerializer.Meta):
        fields = list(ItemSerializer.Meta.fields) + ['active_borrows']

    def get_active_borrows(self, obj):
        records = (
            obj.borrow_records.filter(status=BorrowStatus.ACTIVE)
            .select_related('borrower')
            .order_by('id')
        )
        return [
            {
                'id': record.id,
                'borrower': record.borrower_id,
                'borrower_username': record.borrower.username,
                'quantity': record.quantity,
                'expected_return_date': record.expected_return_date,
                'computed_status': record.computed_status,
            }
            for record in records
        ]
