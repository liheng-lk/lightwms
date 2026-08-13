"""Deletion semantics for consumable operational ledgers.

Deleting a historical ledger entry is an administrative data-retention action,
not a compensating inventory transaction. Current stock therefore stays
unchanged, but every destructive action must be captured by immutable AuditLog.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='ledger_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='ledger_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='ledger_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def item(db, manager):
    warehouse = Warehouse.objects.create(
        code='LEDGER-WH', name='Ledger Warehouse', is_active=True,
    )
    location = Location.objects.create(
        warehouse=warehouse, code='LEDGER-LOC', name='Ledger Location',
        owner=manager, is_active=True,
    )
    return Item.objects.create(
        name='Ledger Consumable', sku='LEDGER-CONS-001',
        owner=manager, location=location,
        type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
        quantity=17, is_active=True,
    )


def make_take(item, ordinary, manager, quantity=2, notes='historical take'):
    return TakeRecord.objects.create(
        item=item, taker=ordinary, operator=manager,
        quantity=quantity, notes=notes,
    )


def make_replenish(item, manager, quantity=3, notes='historical replenish'):
    return ReplenishRecord.objects.create(
        item=item, operator=manager, quantity=quantity, notes=notes,
    )


def assert_delete_audit(*, target_type, record_id, admin, expected):
    log = AuditLog.objects.get(
        action=AuditAction.DELETE,
        target_type=target_type,
        target_id=record_id,
        operator=admin,
    )
    assert log.diff['after'] is None
    before = log.diff['before']
    for key, value in expected.items():
        assert before[key] == value


@pytest.mark.django_db
class TestSingleLedgerDeletion:
    def test_take_delete_keeps_current_stock_and_writes_immutable_audit(
        self, admin, manager, ordinary, item
    ):
        record = make_take(item, ordinary, manager, quantity=4, notes='delete me')
        original_quantity = item.quantity
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.delete(f'/api/v1/take-records/{record.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TakeRecord.objects.filter(id=record.id).exists()
        item.refresh_from_db()
        assert item.quantity == original_quantity
        assert item.status == ItemStatus.IN_STOCK
        assert_delete_audit(
            target_type=TargetType.TAKE_RECORD,
            record_id=record.id,
            admin=admin,
            expected={
                'item_id': item.id,
                'taker_id': ordinary.id,
                'operator_id': manager.id,
                'quantity': 4,
                'notes': 'delete me',
            },
        )

    def test_replenish_delete_keeps_current_stock_and_writes_immutable_audit(
        self, admin, manager, item
    ):
        record = make_replenish(item, manager, quantity=6, notes='delete replenish')
        original_quantity = item.quantity
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.delete(f'/api/v1/replenish-records/{record.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ReplenishRecord.objects.filter(id=record.id).exists()
        item.refresh_from_db()
        assert item.quantity == original_quantity
        assert_delete_audit(
            target_type=TargetType.REPLENISH_RECORD,
            record_id=record.id,
            admin=admin,
            expected={
                'item_id': item.id,
                'operator_id': manager.id,
                'quantity': 6,
                'notes': 'delete replenish',
            },
        )

    @pytest.mark.parametrize('kind', ['take', 'replenish'])
    def test_non_superadmin_cannot_delete_ledger(self, kind, manager, ordinary, item):
        record = (
            make_take(item, ordinary, manager)
            if kind == 'take'
            else make_replenish(item, manager)
        )
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.delete(f'/api/v1/{kind}-records/{record.id}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        model = TakeRecord if kind == 'take' else ReplenishRecord
        assert model.objects.filter(id=record.id).exists()

    @pytest.mark.parametrize('kind', ['take', 'replenish'])
    def test_missing_single_record_returns_404_without_fake_audit(self, kind, admin):
        client = APIClient()
        client.force_authenticate(user=admin)
        target_type = (
            TargetType.TAKE_RECORD if kind == 'take'
            else TargetType.REPLENISH_RECORD
        )

        response = client.delete(f'/api/v1/{kind}-records/999999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not AuditLog.objects.filter(
            action=AuditAction.DELETE,
            target_type=target_type,
            target_id=999999,
        ).exists()


@pytest.mark.django_db
class TestBatchLedgerDeletion:
    @pytest.mark.parametrize('kind', ['take', 'replenish'])
    def test_batch_delete_is_all_or_nothing_when_any_id_is_missing(
        self, kind, admin, manager, ordinary, item
    ):
        first = (
            make_take(item, ordinary, manager, quantity=1, notes='first')
            if kind == 'take'
            else make_replenish(item, manager, quantity=1, notes='first')
        )
        second = (
            make_take(item, ordinary, manager, quantity=2, notes='second')
            if kind == 'take'
            else make_replenish(item, manager, quantity=2, notes='second')
        )
        missing = max(first.id, second.id) + 99999
        original_quantity = item.quantity
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            f'/api/v1/{kind}-records/batch-delete/',
            {'ids': [first.id, missing, second.id]},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        model = TakeRecord if kind == 'take' else ReplenishRecord
        assert model.objects.filter(id=first.id).exists()
        assert model.objects.filter(id=second.id).exists()
        item.refresh_from_db()
        assert item.quantity == original_quantity

    @pytest.mark.parametrize('kind', ['take', 'replenish'])
    def test_batch_delete_writes_one_audit_per_record_and_keeps_stock(
        self, kind, admin, manager, ordinary, item
    ):
        records = [
            (
                make_take(item, ordinary, manager, quantity=i, notes=f'batch-{i}')
                if kind == 'take'
                else make_replenish(item, manager, quantity=i, notes=f'batch-{i}')
            )
            for i in (1, 2, 3)
        ]
        ids = [record.id for record in records]
        original_quantity = item.quantity
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            f'/api/v1/{kind}-records/batch-delete/',
            {'ids': ids},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted'] == 3
        model = TakeRecord if kind == 'take' else ReplenishRecord
        assert not model.objects.filter(id__in=ids).exists()
        item.refresh_from_db()
        assert item.quantity == original_quantity
        target_type = (
            TargetType.TAKE_RECORD if kind == 'take'
            else TargetType.REPLENISH_RECORD
        )
        assert AuditLog.objects.filter(
            action=AuditAction.DELETE,
            target_type=target_type,
            target_id__in=ids,
            operator=admin,
        ).count() == 3

    @pytest.mark.parametrize('kind', ['take', 'replenish'])
    def test_batch_delete_normalizes_duplicate_ids(
        self, kind, admin, manager, ordinary, item
    ):
        record = (
            make_take(item, ordinary, manager)
            if kind == 'take'
            else make_replenish(item, manager)
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            f'/api/v1/{kind}-records/batch-delete/',
            {'ids': [record.id, record.id]},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted'] == 1
