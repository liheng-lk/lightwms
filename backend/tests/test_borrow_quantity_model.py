"""Regression tests defining the multi-quantity reusable borrow model."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='borrow_qty_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='borrow_qty_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def borrower_a(db):
    return User.objects.create_user(
        username='borrower_a', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def borrower_b(db):
    return User.objects.create_user(
        username='borrower_b', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def borrower_c(db):
    return User.objects.create_user(
        username='borrower_c', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def location(db, manager):
    warehouse = Warehouse.objects.create(
        code='BORROW-QTY-WH', name='Borrow Quantity Warehouse', is_active=True
    )
    return Location.objects.create(
        warehouse=warehouse, code='BORROW-QTY-LOC', name='Borrow Quantity Location',
        owner=manager, is_active=True,
    )


def make_item(manager, location, sku='BORROW-QTY-001', quantity=3):
    return Item.objects.create(
        name=sku, sku=sku, owner=manager, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=quantity, is_active=True,
    )


def borrow(client, item, borrower, quantity=1):
    return client.post(f'/api/v1/items/{item.id}/borrow/', {
        'borrower': borrower.id,
        'quantity': quantity,
        'expected_return_date': str(timezone.localdate() + timedelta(days=7)),
        'notes': f'borrow for {borrower.username}',
    }, format='json')


@pytest.mark.django_db
class TestConcurrentBorrowQuantity:
    def test_multiple_users_can_borrow_distinct_units_of_same_item(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item = make_item(manager, location, quantity=3)
        api_client.force_authenticate(user=manager)

        first = borrow(api_client, item, borrower_a, quantity=1)
        second = borrow(api_client, item, borrower_b, quantity=1)

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_201_CREATED
        assert first.data['id'] != second.data['id']
        assert BorrowRecord.objects.filter(item=item, status=BorrowStatus.ACTIVE).count() == 2
        item.refresh_from_db()
        assert item.borrowed_quantity == 2
        assert item.available_quantity == 1
        assert item.status == ItemStatus.AVAILABLE

    def test_final_available_unit_changes_item_to_borrowed(
        self, api_client, manager, borrower_a, borrower_b, borrower_c, location
    ):
        item = make_item(manager, location, quantity=3)
        api_client.force_authenticate(user=manager)

        assert borrow(api_client, item, borrower_a).status_code == 201
        assert borrow(api_client, item, borrower_b).status_code == 201
        assert borrow(api_client, item, borrower_c).status_code == 201

        item.refresh_from_db()
        assert item.borrowed_quantity == 3
        assert item.available_quantity == 0
        assert item.status == ItemStatus.BORROWED

        extra = borrow(api_client, item, borrower_a)
        assert extra.status_code == status.HTTP_409_CONFLICT
        assert extra.data['code'] == 'INSUFFICIENT_QUANTITY'

    def test_single_quantity_item_preserves_item_already_borrowed_semantics(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item = make_item(manager, location, sku='BORROW-SINGLE-001', quantity=1)
        api_client.force_authenticate(user=manager)

        assert borrow(api_client, item, borrower_a).status_code == 201
        second = borrow(api_client, item, borrower_b)

        assert second.status_code == status.HTTP_409_CONFLICT
        assert second.data['code'] == 'ITEM_ALREADY_BORROWED'


@pytest.mark.django_db
class TestTargetedReturn:
    def _two_active(self, api_client, manager, borrower_a, borrower_b, location):
        item = make_item(manager, location, sku='RETURN-QTY-001', quantity=2)
        api_client.force_authenticate(user=manager)
        first = borrow(api_client, item, borrower_a)
        second = borrow(api_client, item, borrower_b)
        assert first.status_code == 201
        assert second.status_code == 201
        return item, first.data['id'], second.data['id']

    def test_borrower_self_return_targets_own_active_record(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item, record_a, record_b = self._two_active(
            api_client, manager, borrower_a, borrower_b, location
        )

        api_client.force_authenticate(user=borrower_b)
        response = api_client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': record_b,
            'return_notes': 'B returned own unit',
            'condition': 'must be ignored for borrower',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == record_b
        assert response.data['borrower'] == borrower_b.id
        assert response.data['condition'] == ''
        assert BorrowRecord.objects.get(id=record_a).status == BorrowStatus.ACTIVE
        assert BorrowRecord.objects.get(id=record_b).status == BorrowStatus.RETURNED
        item.refresh_from_db()
        assert item.borrowed_quantity == 1
        assert item.available_quantity == 1
        assert item.status == ItemStatus.AVAILABLE

    def test_borrower_cannot_return_another_users_record(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item, record_a, record_b = self._two_active(
            api_client, manager, borrower_a, borrower_b, location
        )
        api_client.force_authenticate(user=borrower_b)

        response = api_client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': record_a,
        }, format='json')

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        assert BorrowRecord.objects.get(id=record_a).status == BorrowStatus.ACTIVE
        assert BorrowRecord.objects.get(id=record_b).status == BorrowStatus.ACTIVE

    def test_manager_must_select_record_when_multiple_active_borrows_exist(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item, record_a, record_b = self._two_active(
            api_client, manager, borrower_a, borrower_b, location
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/return/', {
            'return_notes': 'ambiguous manager return',
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'BORROW_RECORD_REQUIRED'
        assert BorrowRecord.objects.get(id=record_a).status == BorrowStatus.ACTIVE
        assert BorrowRecord.objects.get(id=record_b).status == BorrowStatus.ACTIVE

    def test_manager_can_return_selected_active_record(
        self, api_client, manager, borrower_a, borrower_b, location
    ):
        item, record_a, record_b = self._two_active(
            api_client, manager, borrower_a, borrower_b, location
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/return/', {
            'borrow_record_id': record_a,
            'return_notes': 'manager accepted returned unit',
            'condition': 'good',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == record_a
        assert response.data['condition'] == 'good'
        assert BorrowRecord.objects.get(id=record_a).status == BorrowStatus.RETURNED
        assert BorrowRecord.objects.get(id=record_b).status == BorrowStatus.ACTIVE
        item.refresh_from_db()
        assert item.status == ItemStatus.AVAILABLE

    def test_legacy_return_without_record_id_still_works_when_only_one_active(
        self, api_client, manager, borrower_a, location
    ):
        item = make_item(manager, location, sku='RETURN-LEGACY-001', quantity=2)
        api_client.force_authenticate(user=manager)
        created = borrow(api_client, item, borrower_a)
        assert created.status_code == 201

        response = api_client.post(f'/api/v1/items/{item.id}/return/', {
            'return_notes': 'legacy single active return',
            'condition': 'good',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == created.data['id']
        item.refresh_from_db()
        assert item.borrowed_quantity == 0
        assert item.status == ItemStatus.AVAILABLE
