"""Additional quantity and return-record integrity tests."""
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
        username='edge_borrow_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def borrower(db):
    return User.objects.create_user(
        username='edge_borrower', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def location(db, manager):
    warehouse = Warehouse.objects.create(
        code='BORROW-EDGE-WH', name='Borrow Edge Warehouse', is_active=True,
    )
    return Location.objects.create(
        warehouse=warehouse, code='BORROW-EDGE-LOC', name='Borrow Edge Location',
        owner=manager, is_active=True,
    )


def make_item(manager, location, sku, quantity=3):
    return Item.objects.create(
        name=sku, sku=sku, owner=manager, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=quantity, is_active=True,
    )


def borrow_payload(borrower, quantity):
    return {
        'borrower': borrower.id,
        'quantity': quantity,
        'expected_return_date': str(timezone.localdate() + timedelta(days=7)),
        'notes': 'quantity edge test',
    }


@pytest.mark.django_db
class TestBorrowBatchQuantity:
    def test_single_borrow_record_can_represent_multiple_units(
        self, manager, borrower, location
    ):
        item = make_item(manager, location, 'BORROW-EDGE-BATCH', quantity=3)
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.post(
            f'/api/v1/items/{item.id}/borrow/',
            borrow_payload(borrower, 2),
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        record = BorrowRecord.objects.get(id=response.data['id'])
        assert record.quantity == 2
        item.refresh_from_db()
        assert item.borrowed_quantity == 2
        assert item.available_quantity == 1
        assert item.status == ItemStatus.AVAILABLE

        returned = client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': record.id,
            'return_notes': 'return both units',
            'condition': 'good',
        }, format='json')
        assert returned.status_code == status.HTTP_200_OK
        record.refresh_from_db()
        assert record.status == BorrowStatus.RETURNED
        item.refresh_from_db()
        assert item.borrowed_quantity == 0
        assert item.available_quantity == 3
        assert item.status == ItemStatus.AVAILABLE

    def test_over_borrow_does_not_create_partial_record_or_change_status(
        self, manager, borrower, location
    ):
        item = make_item(manager, location, 'BORROW-EDGE-OVER', quantity=2)
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.post(
            f'/api/v1/items/{item.id}/borrow/',
            borrow_payload(borrower, 3),
            format='json',
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'INSUFFICIENT_QUANTITY'
        assert not BorrowRecord.objects.filter(item=item).exists()
        item.refresh_from_db()
        assert item.available_quantity == 2
        assert item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
class TestReturnRecordIntegrity:
    def test_returned_record_id_cannot_be_returned_twice(
        self, manager, borrower, location
    ):
        item = make_item(manager, location, 'BORROW-EDGE-DOUBLE-RETURN', quantity=2)
        record = BorrowRecord.objects.create(
            item=item, borrower=borrower, operator=manager, quantity=1,
            expected_return_date=timezone.localdate() + timedelta(days=1),
            status=BorrowStatus.RETURNED,
            actual_return_datetime=timezone.now(),
        )
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': record.id,
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] in {'NO_ACTIVE_BORROW', 'BORROW_RECORD_NOT_ACTIVE'}
        record.refresh_from_db()
        assert record.status == BorrowStatus.RETURNED

    def test_record_from_another_item_cannot_be_used_for_return(
        self, manager, borrower, location
    ):
        item_a = make_item(manager, location, 'BORROW-EDGE-ITEM-A', quantity=2)
        item_b = make_item(manager, location, 'BORROW-EDGE-ITEM-B', quantity=2)
        record_a = BorrowRecord.objects.create(
            item=item_a, borrower=borrower, operator=manager, quantity=1,
            expected_return_date=timezone.localdate() + timedelta(days=1),
            status=BorrowStatus.ACTIVE,
        )
        record_b = BorrowRecord.objects.create(
            item=item_b, borrower=borrower, operator=manager, quantity=1,
            expected_return_date=timezone.localdate() + timedelta(days=1),
            status=BorrowStatus.ACTIVE,
        )
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.post(f'/api/v1/items/{item_a.id}/return/', {
            'borrow_record_id': record_b.id,
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'BORROW_RECORD_NOT_ACTIVE'
        assert BorrowRecord.objects.get(id=record_a.id).status == BorrowStatus.ACTIVE
        assert BorrowRecord.objects.get(id=record_b.id).status == BorrowStatus.ACTIVE
