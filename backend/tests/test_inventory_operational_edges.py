"""Operational edge tests for item management."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus, ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='opedge_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='opedge_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='opedge_other', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='opedge_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='OPEDGE-WH', name='Operational Edge Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='OPEDGE-LOC', name='Operational Edge Location',
        owner=manager, is_active=True,
    )


@pytest.fixture
def other_location(db, warehouse, other_manager):
    return Location.objects.create(
        warehouse=warehouse, code='OPEDGE-OTHER-LOC', name='Other Operational Location',
        owner=other_manager, is_active=True,
    )


def make_item(*, owner, location, sku, item_type=ItemType.REUSABLE, quantity=1, active=True):
    if item_type == ItemType.REUSABLE:
        item_status = ItemStatus.AVAILABLE
    else:
        item_status = ItemStatus.IN_STOCK if quantity > 0 else ItemStatus.OUT_OF_STOCK
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location,
        type=item_type, status=item_status, quantity=quantity, is_active=active,
    )


def response_text(response):
    content = b''.join(response.streaming_content) if getattr(response, 'streaming', False) else response.content
    return content.decode('utf-8-sig')


@pytest.mark.django_db
class TestCreateQuantityContract:
    def test_reusable_quantity_zero_is_rejected_not_silently_coerced(
        self, api_client, manager, location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/items/', {
            'name': 'Zero reusable',
            'sku': 'OPEDGE-ZERO-REUSE',
            'location': location.id,
            'type': 'reusable',
            'quantity': 0,
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Item.objects.filter(sku='OPEDGE-ZERO-REUSE').exists()


@pytest.mark.django_db
class TestBarcodeIdempotence:
    def test_generate_barcode_twice_returns_same_barcode(
        self, api_client, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='OPEDGE-BARCODE-IDEMP')
        api_client.force_authenticate(user=manager)
        first = api_client.post(f'/api/v1/items/{item.id}/generate-barcode/')
        second = api_client.post(f'/api/v1/items/{item.id}/generate-barcode/')
        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_200_OK
        assert first.data['barcode'] == second.data['barcode']
        item.refresh_from_db()
        assert item.barcode == first.data['barcode']

    def test_inactive_item_cannot_be_found_by_barcode(
        self, api_client, ordinary, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='OPEDGE-INACTIVE-CODE', active=False)
        item.barcode = 'OPEDGE-INACTIVE-BARCODE'
        item.save(update_fields=['barcode'])
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/items/by-barcode/OPEDGE-INACTIVE-BARCODE/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestManagerExportScope:
    def test_item_export_contains_inventory_wide_active_items(
        self, api_client, manager, other_manager, location, other_location
    ):
        own = make_item(owner=manager, location=location, sku='OPEDGE-EXPORT-OWN')
        other = make_item(owner=other_manager, location=other_location, sku='OPEDGE-EXPORT-OTHER')
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/items/export/?file_format=csv')
        assert response.status_code == status.HTTP_200_OK
        text = response_text(response)
        assert own.sku in text
        assert other.sku in text

    def test_borrow_export_contains_inventory_wide_records(
        self, api_client, manager, other_manager, ordinary, location, other_location
    ):
        own = make_item(owner=manager, location=location, sku='OPEDGE-BORROW-OWN')
        other = make_item(owner=other_manager, location=other_location, sku='OPEDGE-BORROW-OTHER')
        BorrowRecord.objects.create(
            item=own, borrower=ordinary, operator=manager, quantity=1,
            expected_return_date=timezone.localdate() + timedelta(days=1),
            notes='OWN_EXPORT_MARKER', status=BorrowStatus.ACTIVE,
        )
        BorrowRecord.objects.create(
            item=other, borrower=ordinary, operator=other_manager, quantity=1,
            expected_return_date=timezone.localdate() + timedelta(days=1),
            notes='OTHER_EXPORT_MARKER', status=BorrowStatus.ACTIVE,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/export/borrow-records/?file_format=csv')
        assert response.status_code == status.HTTP_200_OK
        text = response_text(response)
        assert 'OWN_EXPORT_MARKER' in text
        assert 'OTHER_EXPORT_MARKER' in text


@pytest.mark.django_db
class TestBatchLocationTargetSafety:
    def test_batch_move_to_inactive_location_is_rejected_without_changes(
        self, api_client, manager, location, warehouse
    ):
        item = make_item(owner=manager, location=location, sku='OPEDGE-BATCH-INACTIVE')
        inactive = Location.objects.create(
            warehouse=warehouse, code='OPEDGE-INACTIVE-LOC', name='Inactive target',
            owner=manager, is_active=False,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/items/batch-update-location/', {
            'item_ids': [item.id], 'location_id': inactive.id,
        }, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        item.refresh_from_db()
        assert item.location_id == location.id


@pytest.mark.django_db
class TestHardDeleteHistoryProtection:
    @pytest.mark.parametrize('record_kind', ['borrow', 'take', 'replenish'])
    def test_item_with_any_history_cannot_be_hard_deleted(
        self, api_client, manager, ordinary, location, record_kind
    ):
        item_type = ItemType.REUSABLE if record_kind == 'borrow' else ItemType.CONSUMABLE
        item = make_item(
            owner=manager, location=location, sku=f'OPEDGE-DELETE-{record_kind}',
            item_type=item_type, quantity=5,
        )
        if record_kind == 'borrow':
            BorrowRecord.objects.create(
                item=item, borrower=ordinary, operator=manager, quantity=1,
                expected_return_date=timezone.localdate() + timedelta(days=1),
                status=BorrowStatus.RETURNED,
            )
        elif record_kind == 'take':
            TakeRecord.objects.create(
                item=item, taker=ordinary, operator=manager, quantity=1,
            )
        else:
            ReplenishRecord.objects.create(
                item=item, operator=manager, quantity=1,
            )
        api_client.force_authenticate(user=manager)
        response = api_client.delete(f'/api/v1/items/{item.id}/delete/')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert Item.objects.filter(id=item.id).exists()
