"""End-to-end regression coverage for the Item Manager role contract.

Item Manager is a global inventory-business role. Ownership is responsibility
metadata, not a visibility or mutation boundary. System administration remains
Super Admin only.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus, ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='global_manager_a', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='global_manager_b', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='global_ordinary', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(
        code='GLOBAL-WH', name='Global Role Warehouse', is_active=True,
    )


@pytest.fixture
def locations(warehouse, manager, other_manager):
    return (
        Location.objects.create(
            warehouse=warehouse, code='GLOBAL-A', name='Manager A Location',
            owner=manager, is_active=True,
        ),
        Location.objects.create(
            warehouse=warehouse, code='GLOBAL-B', name='Manager B Location',
            owner=other_manager, is_active=True,
        ),
    )


@pytest.fixture
def other_reusable(locations, other_manager):
    _, loc_b = locations
    return Item.objects.create(
        name='Other Manager Camera', sku='GLOBAL-CAMERA', barcode='GLOBAL-BC-CAMERA',
        location=loc_b, owner=other_manager, type=ItemType.REUSABLE,
        status=ItemStatus.AVAILABLE, quantity=2, is_active=True,
    )


@pytest.fixture
def other_consumable(locations, other_manager):
    _, loc_b = locations
    return Item.objects.create(
        name='Other Manager Cable Tie', sku='GLOBAL-TIE', barcode='GLOBAL-BC-TIE',
        location=loc_b, owner=other_manager, type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK, quantity=10, is_active=True,
    )


def _rows(response):
    return response.data.get('results', response.data)


@pytest.mark.django_db
class TestGlobalInventoryReadScope:
    def test_manager_can_list_search_detail_and_scan_other_owner_item(
        self, client, manager, other_reusable
    ):
        client.force_authenticate(user=manager)

        list_response = client.get('/api/v1/items/', {'page_size': 100})
        search_response = client.get('/api/v1/search/', {
            'keyword': other_reusable.sku, 'page_size': 100,
        })
        detail_response = client.get(f'/api/v1/items/{other_reusable.id}/')
        scan_response = client.get(
            f'/api/v1/items/by-barcode/{other_reusable.barcode}/'
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert other_reusable.id in {row['id'] for row in _rows(list_response)}
        assert search_response.status_code == status.HTTP_200_OK
        assert other_reusable.id in {row['id'] for row in _rows(search_response)}
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data['id'] == other_reusable.id
        assert scan_response.status_code == status.HTTP_200_OK
        assert scan_response.data['id'] == other_reusable.id

    def test_manager_owner_filter_narrows_results_but_does_not_define_visibility(
        self, client, manager, other_manager, locations
    ):
        loc_a, loc_b = locations
        own = Item.objects.create(
            name='Owned', sku='GLOBAL-OWN', location=loc_a, owner=manager,
            type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE, quantity=1,
        )
        other = Item.objects.create(
            name='Other', sku='GLOBAL-OTHER', location=loc_b, owner=other_manager,
            type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE, quantity=1,
        )
        client.force_authenticate(user=manager)

        all_response = client.get('/api/v1/items/', {'page_size': 100})
        filtered_response = client.get('/api/v1/items/', {
            'owner': other_manager.id, 'page_size': 100,
        })

        assert {own.id, other.id}.issubset({row['id'] for row in _rows(all_response)})
        filtered_ids = {row['id'] for row in _rows(filtered_response)}
        assert other.id in filtered_ids
        assert own.id not in filtered_ids

    def test_manager_cannot_expose_inactive_inventory(self, client, manager, other_reusable):
        other_reusable.is_active = False
        other_reusable.save(update_fields=['is_active'])
        client.force_authenticate(user=manager)

        response = client.get('/api/v1/items/', {
            'include_inactive': 'true', 'page_size': 100,
        })
        detail = client.get(f'/api/v1/items/{other_reusable.id}/')

        assert other_reusable.id not in {row['id'] for row in _rows(response)}
        assert detail.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestGlobalInventoryMutationScope:
    def test_manager_can_edit_other_owner_item_and_location(
        self, client, manager, other_reusable, locations
    ):
        _, other_location = locations
        client.force_authenticate(user=manager)

        item_response = client.patch(
            f'/api/v1/items/{other_reusable.id}/',
            {'name': 'Updated by inventory manager'},
            format='json',
        )
        location_response = client.patch(
            f'/api/v1/locations/{other_location.id}/',
            {'name': 'Updated global location'},
            format='json',
        )

        assert item_response.status_code == status.HTTP_200_OK
        assert location_response.status_code == status.HTTP_200_OK
        other_reusable.refresh_from_db()
        other_location.refresh_from_db()
        assert other_reusable.name == 'Updated by inventory manager'
        assert other_location.name == 'Updated global location'

    def test_manager_can_borrow_and_return_other_owner_reusable(
        self, client, manager, ordinary, other_reusable
    ):
        client.force_authenticate(user=manager)
        due = (timezone.localdate() + timedelta(days=7)).isoformat()

        borrow = client.post(
            f'/api/v1/items/{other_reusable.id}/borrow/',
            {'borrower': ordinary.id, 'quantity': 1, 'expected_return_date': due},
            format='json',
        )
        assert borrow.status_code == status.HTTP_201_CREATED

        returned = client.post(
            f'/api/v1/items/{other_reusable.id}/return/',
            {'borrow_record_id': borrow.data['id'], 'return_notes': 'manager return'},
            format='json',
        )
        assert returned.status_code == status.HTTP_200_OK
        assert returned.data['status'] == BorrowStatus.RETURNED

    def test_manager_can_take_and_replenish_other_owner_consumable(
        self, client, manager, ordinary, other_consumable
    ):
        client.force_authenticate(user=manager)

        take = client.post(
            f'/api/v1/items/{other_consumable.id}/take/',
            {'taker': ordinary.id, 'quantity': 3},
            format='json',
        )
        replenish = client.post(
            f'/api/v1/items/{other_consumable.id}/replenish/',
            {'quantity': 2},
            format='json',
        )

        assert take.status_code == status.HTTP_201_CREATED
        assert replenish.status_code == status.HTTP_201_CREATED
        other_consumable.refresh_from_db()
        assert other_consumable.quantity == 9


@pytest.mark.django_db
class TestManagerLedgerAndSystemBoundary:
    def test_manager_sees_cross_owner_operation_ledgers(
        self, client, manager, other_manager, ordinary, other_reusable, other_consumable
    ):
        due = timezone.localdate() + timedelta(days=7)
        BorrowRecord.objects.create(
            item=other_reusable, borrower=ordinary, operator=other_manager,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
        TakeRecord.objects.create(
            item=other_consumable, taker=ordinary, operator=other_manager, quantity=1,
        )
        ReplenishRecord.objects.create(
            item=other_consumable, operator=other_manager, quantity=1,
        )
        client.force_authenticate(user=manager)

        borrow_response = client.get('/api/v1/borrow-records/', {'page_size': 100})
        take_response = client.get('/api/v1/take-records/', {'page_size': 100})
        replenish_response = client.get('/api/v1/replenish-records/', {'page_size': 100})

        assert borrow_response.status_code == status.HTTP_200_OK
        assert take_response.status_code == status.HTTP_200_OK
        assert replenish_response.status_code == status.HTTP_200_OK
        assert any(row['item'] == other_reusable.id for row in _rows(borrow_response))
        assert any(row['item'] == other_consumable.id for row in _rows(take_response))
        assert any(row['item'] == other_consumable.id for row in _rows(replenish_response))

    def test_manager_still_cannot_cross_system_admin_boundary(self, client, manager):
        client.force_authenticate(user=manager)

        assert client.get('/api/v1/users/').status_code == status.HTTP_403_FORBIDDEN
        assert client.post(
            '/api/v1/invite-codes/', {'max_uses': 1}, format='json'
        ).status_code == status.HTTP_403_FORBIDDEN
