"""Lifecycle and numeric-boundary tests for consumable inventory."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


MAX_DB_QUANTITY = 2_147_483_647


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='cons_life_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager_a(db):
    return User.objects.create_user(
        username='cons_life_mgr_a', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def manager_b(db):
    return User.objects.create_user(
        username='cons_life_mgr_b', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def taker(db):
    return User.objects.create_user(
        username='cons_life_taker', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def inventory(db, manager_a, manager_b):
    warehouse = Warehouse.objects.create(
        code='CONS-LIFE-WH', name='Consumable Lifecycle Warehouse', is_active=True,
    )
    loc_a = Location.objects.create(
        warehouse=warehouse, code='CONS-LIFE-A', name='Consumable A',
        owner=manager_a, is_active=True,
    )
    loc_b = Location.objects.create(
        warehouse=warehouse, code='CONS-LIFE-B', name='Consumable B',
        owner=manager_b, is_active=True,
    )
    item = Item.objects.create(
        name='Transferred Consumable', sku='CONS-LIFE-ITEM',
        owner=manager_a, location=loc_a,
        type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
        quantity=10, is_active=True,
    )
    return item, loc_a, loc_b


def result_ids(response):
    return {row['id'] for row in response.data['results']}


def response_text(response):
    content = b''.join(response.streaming_content) if getattr(response, 'streaming', False) else response.content
    return content.decode('utf-8-sig')


@pytest.mark.django_db
class TestOwnershipTransferLedgerScope:
    def test_historical_take_and_replenish_follow_current_item_owner(
        self, manager_a, manager_b, taker, inventory
    ):
        item, _, loc_b = inventory
        take = TakeRecord.objects.create(
            item=item, taker=taker, operator=manager_a,
            quantity=2, notes='TRANSFER-TAKE-HISTORY',
        )
        replenish = ReplenishRecord.objects.create(
            item=item, operator=manager_a,
            quantity=3, notes='TRANSFER-REPLENISH-HISTORY',
        )

        # Responsibility is transferred after the historical movements.
        item.owner = manager_b
        item.location = loc_b
        item.save(update_fields=['owner', 'location', 'updated_at'])

        client = APIClient()
        client.force_authenticate(user=manager_b)
        take_response = client.get('/api/v1/take-records/?page_size=100')
        replenish_response = client.get('/api/v1/replenish-records/?page_size=100')
        assert take_response.status_code == status.HTTP_200_OK
        assert replenish_response.status_code == status.HTTP_200_OK
        assert take.id in result_ids(take_response)
        assert replenish.id in result_ids(replenish_response)

        client.force_authenticate(user=manager_a)
        old_take_response = client.get('/api/v1/take-records/?page_size=100')
        old_replenish_response = client.get('/api/v1/replenish-records/?page_size=100')
        assert take.id not in result_ids(old_take_response)
        assert replenish.id not in result_ids(old_replenish_response)

    def test_exports_follow_current_item_owner_after_transfer(
        self, manager_a, manager_b, taker, inventory
    ):
        item, _, loc_b = inventory
        TakeRecord.objects.create(
            item=item, taker=taker, operator=manager_a,
            quantity=2, notes='TRANSFER-TAKE-EXPORT',
        )
        ReplenishRecord.objects.create(
            item=item, operator=manager_a,
            quantity=3, notes='TRANSFER-REPLENISH-EXPORT',
        )
        item.owner = manager_b
        item.location = loc_b
        item.save(update_fields=['owner', 'location', 'updated_at'])

        client = APIClient()
        client.force_authenticate(user=manager_b)
        new_take = response_text(client.get('/api/v1/export/take-records/?file_format=csv'))
        new_replenish = response_text(client.get('/api/v1/export/replenish-records/?file_format=csv'))
        assert 'TRANSFER-TAKE-EXPORT' in new_take
        assert 'TRANSFER-REPLENISH-EXPORT' in new_replenish

        client.force_authenticate(user=manager_a)
        old_take = response_text(client.get('/api/v1/export/take-records/?file_format=csv'))
        old_replenish = response_text(client.get('/api/v1/export/replenish-records/?file_format=csv'))
        assert 'TRANSFER-TAKE-EXPORT' not in old_take
        assert 'TRANSFER-REPLENISH-EXPORT' not in old_replenish

    def test_only_new_owner_can_operate_stock_after_transfer(
        self, manager_a, manager_b, taker, inventory
    ):
        item, _, loc_b = inventory
        item.owner = manager_b
        item.location = loc_b
        item.save(update_fields=['owner', 'location', 'updated_at'])

        client = APIClient()
        client.force_authenticate(user=manager_a)
        denied = client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': taker.id, 'quantity': 1,
        }, format='json')
        assert denied.status_code == status.HTTP_404_NOT_FOUND

        client.force_authenticate(user=manager_b)
        allowed = client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': taker.id, 'quantity': 1,
        }, format='json')
        assert allowed.status_code == status.HTTP_201_CREATED
        item.refresh_from_db()
        assert item.quantity == 9


@pytest.mark.django_db
class TestConsumableQuantityUpperBound:
    def test_replenish_that_would_overflow_database_integer_is_rejected_cleanly(
        self, manager_a, inventory
    ):
        item, _, _ = inventory
        item.quantity = MAX_DB_QUANTITY
        item.status = ItemStatus.IN_STOCK
        item.save(update_fields=['quantity', 'status'])
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.post(f'/api/v1/items/{item.id}/replenish/', {
            'quantity': 1,
            'notes': 'must not overflow',
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'QUANTITY_OVERFLOW'
        item.refresh_from_db()
        assert item.quantity == MAX_DB_QUANTITY
        assert not ReplenishRecord.objects.filter(item=item, notes='must not overflow').exists()

    def test_large_but_valid_replenish_reaches_database_max_exactly(
        self, manager_a, inventory
    ):
        item, _, _ = inventory
        item.quantity = MAX_DB_QUANTITY - 5
        item.save(update_fields=['quantity'])
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.post(f'/api/v1/items/{item.id}/replenish/', {
            'quantity': 5,
            'notes': 'reach exact max',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        item.refresh_from_db()
        assert item.quantity == MAX_DB_QUANTITY
        assert ReplenishRecord.objects.filter(item=item, quantity=5).exists()
