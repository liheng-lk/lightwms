"""Regression tests for inventory hardening and batch safety."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Category, Item, ItemImage, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus, ReplenishRecord, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='inventory_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='inventory_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='other_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='ordinary_inventory_user', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='INV-WH', name='Inventory Warehouse', is_active=True)


@pytest.fixture
def manager_location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='MGR-LOC', name='Manager Location',
        owner=manager, is_active=True,
    )


@pytest.fixture
def other_location(db, warehouse, other_manager):
    return Location.objects.create(
        warehouse=warehouse, code='OTHER-LOC', name='Other Location',
        owner=other_manager, is_active=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name='Inventory Regression', is_active=True)


def make_item(*, owner, location, sku, item_type=ItemType.REUSABLE, quantity=1):
    status_value = (
        ItemStatus.AVAILABLE if item_type == ItemType.REUSABLE
        else (ItemStatus.IN_STOCK if quantity > 0 else ItemStatus.OUT_OF_STOCK)
    )
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location,
        type=item_type, status=status_value, quantity=quantity, is_active=True,
    )


@pytest.mark.django_db
class TestItemOwnershipBoundary:
    def test_manager_cannot_create_item_for_another_manager(
        self, api_client, manager, other_manager, manager_location
    ):
        api_client.force_authenticate(user=manager)
        response = api_client.post('/api/v1/items/', {
            'name': 'Cross owner item',
            'sku': 'CROSS-OWNER-001',
            'location': manager_location.id,
            'owner': other_manager.id,
            'type': 'reusable',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Item.objects.filter(sku='CROSS-OWNER-001').exists()

    def test_admin_cannot_assign_inventory_to_ordinary_user(
        self, api_client, admin, ordinary, manager_location
    ):
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'Invalid owner role',
            'sku': 'INVALID-OWNER-ROLE',
            'location': manager_location.id,
            'owner': ordinary.id,
            'type': 'reusable',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Item.objects.filter(sku='INVALID-OWNER-ROLE').exists()

    def test_admin_invalid_owner_id_is_safe_4xx(self, api_client, admin, manager_location):
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/v1/items/', {
            'name': 'Missing owner',
            'sku': 'MISSING-OWNER-001',
            'location': manager_location.id,
            'owner': 999999,
            'type': 'reusable',
        })
        assert 400 <= response.status_code < 500
        assert not Item.objects.filter(sku='MISSING-OWNER-001').exists()


@pytest.mark.django_db
class TestBatchInventorySafety:
    def test_manager_batch_location_cannot_move_other_managers_item(
        self, api_client, manager, other_manager, manager_location, other_location
    ):
        own = make_item(owner=manager, location=manager_location, sku='BATCH-OWN-001')
        other = make_item(owner=other_manager, location=other_location, sku='BATCH-OTHER-001')
        api_client.force_authenticate(user=manager)

        response = api_client.post('/api/v1/items/batch-update-location/', {
            'item_ids': [own.id, other.id],
            'location_id': other_location.id,
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        own.refresh_from_db()
        other.refresh_from_db()
        # Mixed batches must be all-or-nothing on a permission failure.
        assert own.location_id == manager_location.id
        assert other.location_id == other_location.id

    def test_manager_batch_delete_cannot_delete_other_managers_item(
        self, api_client, manager, other_manager, manager_location, other_location
    ):
        own = make_item(owner=manager, location=manager_location, sku='DELETE-OWN-001')
        other = make_item(owner=other_manager, location=other_location, sku='DELETE-OTHER-001')
        api_client.force_authenticate(user=manager)

        response = api_client.post('/api/v1/items/batch-delete/', {
            'ids': [own.id, other.id],
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Item.objects.filter(id=own.id).exists()
        assert Item.objects.filter(id=other.id).exists()

    def test_admin_batch_delete_rolls_back_when_any_item_is_not_deletable(
        self, api_client, admin, manager, ordinary, manager_location
    ):
        deletable = make_item(owner=manager, location=manager_location, sku='DELETE-ATOMIC-OK')
        protected = make_item(owner=manager, location=manager_location, sku='DELETE-ATOMIC-BLOCK')
        BorrowRecord.objects.create(
            item=protected, borrower=ordinary, operator=manager,
            quantity=1, expected_return_date=timezone.localdate() + timedelta(days=1),
            status=BorrowStatus.RETURNED,
        )
        api_client.force_authenticate(user=admin)

        response = api_client.post('/api/v1/items/batch-delete/', {
            'ids': [deletable.id, protected.id],
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert Item.objects.filter(id=deletable.id).exists()
        assert Item.objects.filter(id=protected.id).exists()


@pytest.mark.django_db
class TestCreateWithInvoiceAtomicity:
    def test_missing_invoice_metadata_does_not_create_item(
        self, api_client, manager, manager_location
    ):
        api_client.force_authenticate(user=manager)
        invoice = SimpleUploadedFile('invoice.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = api_client.post('/api/v1/items/with-invoice/', {
            'name': 'Should not persist',
            'sku': 'INVOICE-ATOMIC-001',
            'location': manager_location.id,
            'type': 'reusable',
            'invoice_file': invoice,
            # invoice_amount / invoice_category intentionally omitted
        }, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Item.objects.filter(sku='INVOICE-ATOMIC-001').exists()


@pytest.mark.django_db
class TestImageOwnershipBoundary:
    def test_manager_cannot_set_other_managers_primary_image(
        self, api_client, manager, other_manager, other_location
    ):
        item = make_item(owner=other_manager, location=other_location, sku='IMAGE-OTHER-001')
        image = ItemImage.objects.create(
            item=item,
            original='items/x/original.webp',
            thumb_256='items/x/256.webp',
            thumb_768='items/x/768.webp',
            thumb_1600='items/x/1600.webp',
            is_primary=False,
        )
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/items/{item.id}/images/{image.id}/set-primary/', {}, format='json'
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        image.refresh_from_db()
        assert image.is_primary is False


@pytest.mark.django_db
class TestBulkExportBoundary:
    def test_ordinary_user_cannot_bulk_export_items(
        self, api_client, ordinary, manager, manager_location
    ):
        make_item(owner=manager, location=manager_location, sku='EXPORT-ITEM-001')
        api_client.force_authenticate(user=ordinary)
        response = api_client.get('/api/v1/items/export/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize('path', [
        '/api/v1/export/borrow-records/',
        '/api/v1/export/take-records/',
        '/api/v1/export/replenish-records/',
    ])
    def test_ordinary_user_cannot_bulk_export_operational_records(
        self, api_client, ordinary, path
    ):
        api_client.force_authenticate(user=ordinary)
        response = api_client.get(path)
        assert response.status_code == status.HTTP_403_FORBIDDEN
