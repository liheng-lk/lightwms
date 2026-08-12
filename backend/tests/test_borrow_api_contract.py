"""API contract tests for quantity-aware borrow presentation and return selection."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='contract_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def borrower_a(db):
    return User.objects.create_user(
        username='contract_a', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def borrower_b(db):
    return User.objects.create_user(
        username='contract_b', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def item(db, manager):
    warehouse = Warehouse.objects.create(
        code='CONTRACT-WH', name='Contract Warehouse', is_active=True,
    )
    location = Location.objects.create(
        warehouse=warehouse, code='CONTRACT-LOC', name='Contract Location',
        owner=manager, is_active=True,
    )
    return Item.objects.create(
        name='Contract item', sku='CONTRACT-ITEM', owner=manager, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=3, is_active=True,
    )


def add_active(item, manager, borrower, quantity=1):
    return BorrowRecord.objects.create(
        item=item, borrower=borrower, operator=manager, quantity=quantity,
        expected_return_date=timezone.localdate() + timedelta(days=5),
        status=BorrowStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestItemBorrowPresentation:
    def test_item_detail_lists_all_active_borrows(self, manager, borrower_a, borrower_b, item):
        record_a = add_active(item, manager, borrower_a)
        record_b = add_active(item, manager, borrower_b)
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.get(f'/api/v1/items/{item.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert {row['id'] for row in response.data['active_borrows']} == {record_a.id, record_b.id}
        assert {row['borrower'] for row in response.data['active_borrows']} == {borrower_a.id, borrower_b.id}
        assert sum(row['quantity'] for row in response.data['active_borrows']) == 2
        # Singular legacy fields must not pretend the first borrower represents
        # the whole multi-borrow state.
        assert response.data['current_borrower'] is None
        assert response.data['current_borrow_record_id'] is None

    def test_single_active_borrow_keeps_legacy_singular_fields(self, manager, borrower_a, item):
        record = add_active(item, manager, borrower_a, quantity=2)
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.get(f'/api/v1/items/{item.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['active_borrows']) == 1
        assert response.data['current_borrower'] == borrower_a.username
        assert response.data['current_borrow_record_id'] == record.id
        assert response.data['active_borrows'][0]['quantity'] == 2


@pytest.mark.django_db
class TestSameBorrowerMultipleRecords:
    def test_same_borrower_with_multiple_active_records_must_select_one(
        self, manager, borrower_a, item
    ):
        first = add_active(item, manager, borrower_a)
        second = add_active(item, manager, borrower_a)
        client = APIClient()
        client.force_authenticate(user=borrower_a)

        ambiguous = client.post(f'/api/v1/items/{item.id}/return/', {}, format='json')
        assert ambiguous.status_code == status.HTTP_409_CONFLICT
        assert ambiguous.data['code'] == 'BORROW_RECORD_REQUIRED'

        targeted = client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': second.id,
            'return_notes': 'return second batch',
        }, format='json')
        assert targeted.status_code == status.HTTP_200_OK
        assert targeted.data['id'] == second.id
        assert BorrowRecord.objects.get(id=first.id).status == BorrowStatus.ACTIVE
        assert BorrowRecord.objects.get(id=second.id).status == BorrowStatus.RETURNED
