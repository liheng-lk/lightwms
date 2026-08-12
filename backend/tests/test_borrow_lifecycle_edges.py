"""Borrow lifecycle tests across account and ownership changes."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='life_borrow_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager_a(db):
    return User.objects.create_user(
        username='life_borrow_mgr_a', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def manager_b(db):
    return User.objects.create_user(
        username='life_borrow_mgr_b', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def borrower_a(db):
    return User.objects.create_user(
        username='life_borrower_a', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def borrower_b(db):
    return User.objects.create_user(
        username='life_borrower_b', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def setup_inventory(db, manager_a, manager_b):
    warehouse = Warehouse.objects.create(
        code='BORROW-LIFE-WH', name='Borrow Lifecycle Warehouse', is_active=True,
    )
    loc_a = Location.objects.create(
        warehouse=warehouse, code='BORROW-LIFE-A', name='Borrow Lifecycle A',
        owner=manager_a, is_active=True,
    )
    loc_b = Location.objects.create(
        warehouse=warehouse, code='BORROW-LIFE-B', name='Borrow Lifecycle B',
        owner=manager_b, is_active=True,
    )
    item_a = Item.objects.create(
        name='Borrow Life A', sku='BORROW-LIFE-ITEM-A', owner=manager_a,
        location=loc_a, type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=3, is_active=True,
    )
    item_b = Item.objects.create(
        name='Borrow Life B', sku='BORROW-LIFE-ITEM-B', owner=manager_b,
        location=loc_b, type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=2, is_active=True,
    )
    return item_a, item_b, loc_a, loc_b


def active_record(item, borrower, operator, quantity=1):
    return BorrowRecord.objects.create(
        item=item,
        borrower=borrower,
        operator=operator,
        quantity=quantity,
        expected_return_date=timezone.localdate() + timedelta(days=5),
        status=BorrowStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestBorrowRecordVisibility:
    def test_ordinary_user_list_contains_only_own_records(
        self, borrower_a, borrower_b, manager_a, setup_inventory
    ):
        item_a, _, _, _ = setup_inventory
        own = active_record(item_a, borrower_a, manager_a)
        other = active_record(item_a, borrower_b, manager_a)
        client = APIClient()
        client.force_authenticate(user=borrower_a)

        response = client.get('/api/v1/borrow-records/?status=active&page_size=100')

        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert own.id in ids
        assert other.id not in ids

    def test_manager_list_contains_only_current_owned_inventory_records(
        self, borrower_a, manager_a, manager_b, setup_inventory
    ):
        item_a, item_b, _, _ = setup_inventory
        own = active_record(item_a, borrower_a, manager_a)
        other = active_record(item_b, borrower_a, manager_b)
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.get('/api/v1/borrow-records/?status=active&page_size=100')

        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert own.id in ids
        assert other.id not in ids


@pytest.mark.django_db
class TestBorrowLifecycleAfterAccountChanges:
    def test_disabled_borrower_history_remains_returnable_by_manager(
        self, borrower_a, manager_a, setup_inventory
    ):
        item_a, _, _, _ = setup_inventory
        record = active_record(item_a, borrower_a, manager_a, quantity=2)
        item_a.status = ItemStatus.AVAILABLE
        item_a.save(update_fields=['status'])
        borrower_a.is_active = False
        borrower_a.save(update_fields=['is_active'])
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.post(f'/api/v1/items/{item_a.id}/return/', {
            'borrow_record_id': record.id,
            'return_notes': 'returned after borrower account disabled',
            'condition': 'good',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        record.refresh_from_db()
        assert record.status == BorrowStatus.RETURNED
        item_a.refresh_from_db()
        assert item_a.borrowed_quantity == 0
        assert item_a.available_quantity == item_a.quantity

    def test_new_owner_can_return_existing_borrow_after_reassignment(
        self, borrower_a, manager_a, manager_b, setup_inventory
    ):
        item_a, _, _, loc_b = setup_inventory
        record = active_record(item_a, borrower_a, manager_a)
        # Simulate a super-admin ownership transfer while a historical borrow is active.
        item_a.owner = manager_b
        item_a.location = loc_b
        item_a.save(update_fields=['owner', 'location', 'updated_at'])
        client = APIClient()
        client.force_authenticate(user=manager_b)

        response = client.post(f'/api/v1/items/{item_a.id}/return/', {
            'borrow_record_id': record.id,
            'return_notes': 'accepted by new responsible manager',
            'condition': 'good',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        record.refresh_from_db()
        assert record.status == BorrowStatus.RETURNED

    def test_previous_owner_loses_return_permission_after_reassignment(
        self, borrower_a, manager_a, manager_b, setup_inventory
    ):
        item_a, _, _, loc_b = setup_inventory
        record = active_record(item_a, borrower_a, manager_a)
        item_a.owner = manager_b
        item_a.location = loc_b
        item_a.save(update_fields=['owner', 'location', 'updated_at'])
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.post(f'/api/v1/items/{item_a.id}/return/', {
            'borrow_record_id': record.id,
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        record.refresh_from_db()
        assert record.status == BorrowStatus.ACTIVE
