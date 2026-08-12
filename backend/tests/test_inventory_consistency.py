"""Inventory consistency tests beyond basic permission checks."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


HEADERS = (
    'name,sku,type,warehouse_code,location_code,barcode,quantity,unit,'
    'description,category_path,owner_username_or_phone\n'
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='consistency_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='consistency_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='consistency_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='CONS-WH', name='Consistency Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='CONS-LOC', name='Consistency Location',
        owner=manager, is_active=True,
    )


def make_reusable(*, owner, location, sku, quantity=1):
    return Item.objects.create(
        name=sku, sku=sku, owner=owner, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=quantity, is_active=True,
    )


def upload_csv(api_client, content):
    upload = SimpleUploadedFile('items.csv', content.encode('utf-8'), content_type='text/csv')
    return api_client.post(
        '/api/v1/items/import/',
        {'file': upload, 'allow_partial': 'true'},
        format='multipart',
    )


@pytest.mark.django_db
class TestReusableQuantityConsistency:
    def test_reducing_total_to_borrowed_quantity_marks_item_fully_borrowed(
        self, api_client, manager, ordinary, location
    ):
        item = make_reusable(owner=manager, location=location, sku='QTY-SYNC-001', quantity=2)
        BorrowRecord.objects.create(
            item=item, borrower=ordinary, operator=manager,
            quantity=1, expected_return_date=timezone.localdate() + timedelta(days=3),
            status=BorrowStatus.ACTIVE,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.patch(
            f'/api/v1/items/{item.id}/', {'quantity': 1}, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.quantity == 1
        assert item.available_quantity == 0
        assert item.status == ItemStatus.BORROWED

    def test_consumable_quantity_cannot_be_silently_edited_through_item_patch(
        self, api_client, manager, location
    ):
        item = Item.objects.create(
            name='Consumable', sku='CONSUMABLE-PATCH-001', owner=manager,
            location=location, type=ItemType.CONSUMABLE,
            status=ItemStatus.IN_STOCK, quantity=5, is_active=True,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.patch(
            f'/api/v1/items/{item.id}/', {'quantity': 20}, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        item.refresh_from_db()
        assert item.quantity == 5

    def test_active_borrow_blocks_item_deactivation(
        self, api_client, manager, ordinary, location
    ):
        item = make_reusable(owner=manager, location=location, sku='DEACT-BORROW-001')
        BorrowRecord.objects.create(
            item=item, borrower=ordinary, operator=manager,
            quantity=1, expected_return_date=timezone.localdate() + timedelta(days=3),
            status=BorrowStatus.ACTIVE,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(f'/api/v1/items/{item.id}/deactivate/')

        assert response.status_code == status.HTTP_409_CONFLICT
        item.refresh_from_db()
        assert item.is_active is True


@pytest.mark.django_db
class TestItemImportConsistency:
    def test_reusable_import_creates_integer_quantity(
        self, api_client, admin, warehouse, location
    ):
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Imported reusable,IMPORT-REUSE-001,reusable,{warehouse.code},{location.code},,3,pcs,,,\n'
        )

        response = upload_csv(api_client, content)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['create_count'] == 1
        item = Item.objects.get(sku='IMPORT-REUSE-001')
        assert item.quantity == 3
        assert item.status == ItemStatus.AVAILABLE

    def test_import_cannot_assign_inventory_to_ordinary_user(
        self, api_client, admin, ordinary, warehouse, location
    ):
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Bad owner,IMPORT-OWNER-001,reusable,{warehouse.code},{location.code},,1,pcs,,,{ordinary.username}\n'
        )

        response = upload_csv(api_client, content)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['create_count'] == 0
        assert response.data['error_count'] >= 1
        assert not Item.objects.filter(sku='IMPORT-OWNER-001').exists()

    def test_partial_import_recovers_after_duplicate_barcode(
        self, api_client, admin, manager, warehouse, location
    ):
        Item.objects.create(
            name='Existing barcode', sku='EXISTING-BARCODE-001', barcode='DUP-BARCODE-001',
            owner=manager, location=location, type=ItemType.REUSABLE,
            status=ItemStatus.AVAILABLE, quantity=1, is_active=True,
        )
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Duplicate barcode,IMPORT-DUP-001,reusable,{warehouse.code},{location.code},DUP-BARCODE-001,1,pcs,,,\n'
            f'Valid after error,IMPORT-VALID-002,reusable,{warehouse.code},{location.code},,2,pcs,,,\n'
        )

        response = upload_csv(api_client, content)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['error_count'] >= 1
        assert response.data['create_count'] == 1
        assert not Item.objects.filter(sku='IMPORT-DUP-001').exists()
        assert Item.objects.filter(sku='IMPORT-VALID-002').exists()
