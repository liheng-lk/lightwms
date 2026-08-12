"""Regression tests for consumable take/replenish operations."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='consumable_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='consumable_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='consumable_other_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='consumable_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def other_ordinary(db):
    return User.objects.create_user(
        username='consumable_other_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def disabled_user(db):
    return User.objects.create_user(
        username='consumable_disabled', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=False,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(
        code='CONS-WH-OPS', name='Consumable Operations Warehouse', is_active=True,
    )


@pytest.fixture
def manager_location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='CONS-LOC-A', name='Consumable A',
        owner=manager, is_active=True,
    )


@pytest.fixture
def other_location(db, warehouse, other_manager):
    return Location.objects.create(
        warehouse=warehouse, code='CONS-LOC-B', name='Consumable B',
        owner=other_manager, is_active=True,
    )


def make_consumable(*, owner, location, sku, quantity=5, active=True):
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location,
        type=ItemType.CONSUMABLE,
        status=ItemStatus.IN_STOCK if quantity > 0 else ItemStatus.OUT_OF_STOCK,
        quantity=quantity, is_active=active,
    )


def make_reusable(*, owner, location, sku, quantity=2):
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=quantity, is_active=True,
    )


@pytest.mark.django_db
class TestTakeInventoryInvariant:
    def test_take_exact_stock_sets_out_of_stock_and_creates_ledger(
        self, api_client, manager, ordinary, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-TAKE-EXACT', quantity=5,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': ordinary.id,
            'quantity': 5,
            'notes': 'exact stock take',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        item.refresh_from_db()
        assert item.quantity == 0
        assert item.status == ItemStatus.OUT_OF_STOCK
        record = TakeRecord.objects.get(id=response.data['id'])
        assert record.item_id == item.id
        assert record.taker_id == ordinary.id
        assert record.operator_id == manager.id
        assert record.quantity == 5
        assert record.notes == 'exact stock take'
        assert AuditLog.objects.filter(
            action=AuditAction.TAKE,
            target_type=TargetType.ITEM,
            target_id=item.id,
            operator=manager,
        ).exists()

    def test_partial_take_keeps_in_stock(
        self, api_client, manager, ordinary, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-TAKE-PARTIAL', quantity=5,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': ordinary.id, 'quantity': 2,
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        item.refresh_from_db()
        assert item.quantity == 3
        assert item.status == ItemStatus.IN_STOCK
        assert TakeRecord.objects.filter(item=item, quantity=2).count() == 1

    def test_overtake_does_not_mutate_inventory_or_create_record(
        self, api_client, manager, ordinary, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-TAKE-OVER', quantity=2,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': ordinary.id, 'quantity': 3,
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'INSUFFICIENT_QUANTITY'
        item.refresh_from_db()
        assert item.quantity == 2
        assert item.status == ItemStatus.IN_STOCK
        assert not TakeRecord.objects.filter(item=item).exists()

    def test_zero_quantity_take_is_rejected_before_mutation(
        self, api_client, manager, ordinary, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-TAKE-ZERO', quantity=2,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': ordinary.id, 'quantity': 0,
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        item.refresh_from_db()
        assert item.quantity == 2
        assert not TakeRecord.objects.filter(item=item).exists()

    def test_disabled_taker_is_rejected_without_mutation(
        self, api_client, manager, disabled_user, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-TAKE-DISABLED', quantity=2,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/items/{item.id}/take/', {
            'taker': disabled_user.id, 'quantity': 1,
        }, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'TAKER_INACTIVE'
        item.refresh_from_db()
        assert item.quantity == 2
        assert not TakeRecord.objects.filter(item=item).exists()


@pytest.mark.django_db
class TestReplenishInventoryInvariant:
    def test_replenish_zero_stock_sets_in_stock_and_creates_ledger(
        self, api_client, manager, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-REPLENISH-ZERO', quantity=0,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/items/{item.id}/replenish/', {
            'quantity': 4, 'notes': 'new shipment',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        item.refresh_from_db()
        assert item.quantity == 4
        assert item.status == ItemStatus.IN_STOCK
        record = ReplenishRecord.objects.get(id=response.data['id'])
        assert record.item_id == item.id
        assert record.operator_id == manager.id
        assert record.quantity == 4
        assert record.notes == 'new shipment'
        assert AuditLog.objects.filter(
            action=AuditAction.REPLENISH,
            target_type=TargetType.ITEM,
            target_id=item.id,
            operator=manager,
        ).exists()

    def test_zero_quantity_replenish_is_rejected_before_mutation(
        self, api_client, manager, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-REPLENISH-ZERO-QTY', quantity=1,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(f'/api/v1/items/{item.id}/replenish/', {
            'quantity': 0,
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        item.refresh_from_db()
        assert item.quantity == 1
        assert not ReplenishRecord.objects.filter(item=item).exists()


@pytest.mark.django_db
class TestConsumableOperationPermissions:
    @pytest.mark.parametrize('operation,payload_factory', [
        ('take', lambda ordinary: {'taker': ordinary.id, 'quantity': 1}),
        ('replenish', lambda ordinary: {'quantity': 1}),
    ])
    def test_ordinary_user_cannot_mutate_stock(
        self, api_client, ordinary, manager, manager_location, operation, payload_factory
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku=f'CONS-ORDINARY-{operation}', quantity=3,
        )
        api_client.force_authenticate(user=ordinary)
        response = api_client.post(
            f'/api/v1/items/{item.id}/{operation}/',
            payload_factory(ordinary), format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        item.refresh_from_db()
        assert item.quantity == 3

    @pytest.mark.parametrize('operation,payload_factory', [
        ('take', lambda ordinary: {'taker': ordinary.id, 'quantity': 1}),
        ('replenish', lambda ordinary: {'quantity': 1}),
    ])
    def test_manager_cannot_mutate_other_managers_stock(
        self, api_client, manager, other_manager, ordinary,
        other_location, operation, payload_factory
    ):
        item = make_consumable(
            owner=other_manager, location=other_location,
            sku=f'CONS-CROSS-{operation}', quantity=3,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{item.id}/{operation}/',
            payload_factory(ordinary), format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        item.refresh_from_db()
        assert item.quantity == 3

    @pytest.mark.parametrize('operation,payload_factory', [
        ('take', lambda ordinary: {'taker': ordinary.id, 'quantity': 1}),
        ('replenish', lambda ordinary: {'quantity': 1}),
    ])
    def test_reusable_item_rejects_consumable_operations(
        self, api_client, manager, ordinary, manager_location, operation, payload_factory
    ):
        item = make_reusable(
            owner=manager, location=manager_location,
            sku=f'REUSE-{operation}', quantity=2,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{item.id}/{operation}/',
            payload_factory(ordinary), format='json'
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'INVALID_ITEM_TYPE'
        item.refresh_from_db()
        assert item.quantity == 2

    @pytest.mark.parametrize('operation,payload_factory', [
        ('take', lambda ordinary: {'taker': ordinary.id, 'quantity': 1}),
        ('replenish', lambda ordinary: {'quantity': 1}),
    ])
    def test_inactive_consumable_rejects_operations(
        self, api_client, manager, ordinary, manager_location, operation, payload_factory
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku=f'CONS-INACTIVE-{operation}', quantity=3, active=False,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{item.id}/{operation}/',
            payload_factory(ordinary), format='json'
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'RESOURCE_INACTIVE'
        item.refresh_from_db()
        assert item.quantity == 3


@pytest.mark.django_db
class TestConsumableRecordVisibility:
    def test_ordinary_user_sees_only_own_take_records(
        self, api_client, ordinary, other_ordinary, manager, manager_location
    ):
        item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-RECORD-ORDINARY', quantity=10,
        )
        own = TakeRecord.objects.create(
            item=item, taker=ordinary, operator=manager, quantity=1, notes='OWN-TAKE'
        )
        other = TakeRecord.objects.create(
            item=item, taker=other_ordinary, operator=manager, quantity=1, notes='OTHER-TAKE'
        )
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/take-records/?page_size=100')
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert own.id in ids
        assert other.id not in ids

    def test_manager_sees_only_current_owned_item_take_records(
        self, api_client, ordinary, manager, other_manager,
        manager_location, other_location
    ):
        own_item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-RECORD-MGR-OWN', quantity=5,
        )
        other_item = make_consumable(
            owner=other_manager, location=other_location,
            sku='CONS-RECORD-MGR-OTHER', quantity=5,
        )
        own = TakeRecord.objects.create(
            item=own_item, taker=ordinary, operator=manager, quantity=1
        )
        other = TakeRecord.objects.create(
            item=other_item, taker=ordinary, operator=other_manager, quantity=1
        )
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/take-records/?page_size=100')
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert own.id in ids
        assert other.id not in ids

    def test_ordinary_user_cannot_list_replenish_records(
        self, api_client, ordinary
    ):
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/replenish-records/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_sees_only_current_owned_item_replenish_records(
        self, api_client, manager, other_manager, manager_location, other_location
    ):
        own_item = make_consumable(
            owner=manager, location=manager_location,
            sku='CONS-REPL-MGR-OWN', quantity=5,
        )
        other_item = make_consumable(
            owner=other_manager, location=other_location,
            sku='CONS-REPL-MGR-OTHER', quantity=5,
        )
        own = ReplenishRecord.objects.create(
            item=own_item, operator=manager, quantity=1
        )
        other = ReplenishRecord.objects.create(
            item=other_item, operator=other_manager, quantity=1
        )
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/replenish-records/?page_size=100')
        assert response.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in response.data['results']}
        assert own.id in ids
        assert other.id not in ids
