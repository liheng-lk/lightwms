"""Borrow-aware inventory serializers."""
from rest_framework import serializers

from apps.operations.models import BorrowStatus
from apps.users.models import UserRole

from .serializers import ItemByBarcodeSerializer, ItemSerializer


class ActiveBorrowMixin:
    """Reusable helpers for serializing role-scoped active borrow state."""

    def _all_active_records(self, obj):
        cache_name = '_borrow_aware_all_active_records'
        if not hasattr(obj, cache_name):
            records = list(
                obj.borrow_records.filter(status=BorrowStatus.ACTIVE)
                .select_related('borrower')
                .order_by('id')
            )
            setattr(obj, cache_name, records)
        return getattr(obj, cache_name)

    def _active_records(self, obj):
        """Return records visible to the requesting user.

        Managers reach only their owned items through the hardened views, so
        they may see all active records for operational return handling.
        Ordinary users may browse inventory but must only see their own borrow
        transactions; exposing coworkers here would leak personnel activity.
        """
        records = self._all_active_records(obj)
        request = self.context.get('request') if hasattr(self, 'context') else None
        user = getattr(request, 'user', None)
        if user and getattr(user, 'role', None) == UserRole.READ_ONLY_USER:
            return [record for record in records if record.borrower_id == user.id]
        return records

    def _single_active_record(self, obj):
        records = self._active_records(obj)
        return records[0] if len(records) == 1 else None

    def get_active_borrows(self, obj):
        return [
            {
                'id': record.id,
                'borrower': record.borrower_id,
                'borrower_username': record.borrower.username,
                'quantity': record.quantity,
                'expected_return_date': record.expected_return_date,
                'computed_status': record.computed_status,
            }
            for record in self._active_records(obj)
        ]


class BorrowAwareItemSerializer(ActiveBorrowMixin, ItemSerializer):
    """Item detail serializer with role-scoped active borrow records.

    Existing singular borrow fields remain for backward compatibility, but are
    populated only when exactly one *visible* active record exists. New clients
    should use `active_borrows` for quantity-aware behavior.
    """
    active_borrows = serializers.SerializerMethodField()

    class Meta(ItemSerializer.Meta):
        fields = list(ItemSerializer.Meta.fields) + ['active_borrows']

    def get_current_borrower(self, obj):
        record = self._single_active_record(obj)
        return record.borrower.username if record else None

    def get_current_borrow_record_id(self, obj):
        record = self._single_active_record(obj)
        return record.id if record else None

    def get_current_expected_return_date(self, obj):
        record = self._single_active_record(obj)
        return record.expected_return_date if record else None

    def get_days_overdue(self, obj):
        record = self._single_active_record(obj)
        if not record:
            return None
        from django.utils import timezone
        today = timezone.localdate()
        if record.expected_return_date < today:
            return (today - record.expected_return_date).days
        return 0


class BorrowAwareBarcodeSerializer(ActiveBorrowMixin, ItemByBarcodeSerializer):
    """Scanner response with the same quantity-aware borrow state as detail."""
    active_borrows = serializers.SerializerMethodField()
    available_quantity = serializers.IntegerField(read_only=True)
    borrowed_quantity = serializers.IntegerField(read_only=True)

    class Meta(ItemByBarcodeSerializer.Meta):
        fields = list(ItemByBarcodeSerializer.Meta.fields) + [
            'available_quantity',
            'borrowed_quantity',
            'active_borrows',
        ]
