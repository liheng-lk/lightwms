"""Semantic and lifecycle regression tests for inventory management."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Category, Item, ItemImage, ItemStatus, ItemType, Location, Warehouse
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
        username='semantic_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='semantic_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def borrower(db):
    return User.objects.create_user(
        username='semantic_borrower', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='SEM-WH', name='Semantic Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='SEM-LOC', name='Semantic Location',
        owner=manager, is_active=True,
    )


def make_item(*, owner, location, sku, barcode=None, quantity=1):
    return Item.objects.create(
        name=sku, sku=sku, barcode=barcode, owner=owner, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=quantity, is_active=True,
    )


def upload_csv(api_client, content, allow_partial=True):
    upload = SimpleUploadedFile('items.csv', content.encode('utf-8'), content_type='text/csv')
    return api_client.post(
        '/api/v1/items/import/',
        {'file': upload, 'allow_partial': str(allow_partial).lower()},
        format='multipart',
    )


@pytest.mark.django_db
class TestUniqueConstraintSemantics:
    def test_duplicate_sku_returns_specific_business_code(
        self, api_client, manager, location
    ):
        make_item(owner=manager, location=location, sku='SEM-DUP-SKU')
        api_client.force_authenticate(user=manager)

        response = api_client.post('/api/v1/items/', {
            'name': 'Duplicate SKU',
            'sku': 'SEM-DUP-SKU',
            'location': location.id,
            'type': 'reusable',
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'DUPLICATE_SKU'

    def test_duplicate_barcode_returns_specific_business_code(
        self, api_client, manager, location
    ):
        make_item(
            owner=manager, location=location,
            sku='SEM-BARCODE-BASE', barcode='SEM-DUP-BARCODE'
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post('/api/v1/items/', {
            'name': 'Duplicate barcode',
            'sku': 'SEM-BARCODE-NEW',
            'barcode': 'SEM-DUP-BARCODE',
            'location': location.id,
            'type': 'reusable',
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'DUPLICATE_BARCODE'

    def test_duplicate_barcode_on_update_does_not_modify_item(
        self, api_client, manager, location
    ):
        first = make_item(
            owner=manager, location=location,
            sku='SEM-BARCODE-FIRST', barcode='SEM-UPDATE-BARCODE'
        )
        second = make_item(owner=manager, location=location, sku='SEM-BARCODE-SECOND')
        api_client.force_authenticate(user=manager)

        response = api_client.patch(
            f'/api/v1/items/{second.id}/',
            {'barcode': first.barcode},
            format='json',
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['code'] == 'DUPLICATE_BARCODE'
        second.refresh_from_db()
        assert second.barcode is None


@pytest.mark.django_db
class TestImagePrimaryLifecycle:
    def test_setting_new_primary_keeps_exactly_one_primary(
        self, api_client, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='SEM-IMG-PRIMARY')
        first = ItemImage.objects.create(
            item=item, original='items/a/original.webp', thumb_256='items/a/256.webp',
            thumb_768='items/a/768.webp', thumb_1600='items/a/1600.webp', is_primary=True,
        )
        second = ItemImage.objects.create(
            item=item, original='items/b/original.webp', thumb_256='items/b/256.webp',
            thumb_768='items/b/768.webp', thumb_1600='items/b/1600.webp', is_primary=False,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.post(
            f'/api/v1/items/{item.id}/images/{second.id}/set-primary/', {}, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.is_primary is False
        assert second.is_primary is True
        assert ItemImage.objects.filter(item=item, is_primary=True).count() == 1

    def test_deleting_primary_promotes_remaining_image(
        self, api_client, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='SEM-IMG-DELETE')
        first = ItemImage.objects.create(
            item=item, original='items/c/original.webp', thumb_256='items/c/256.webp',
            thumb_768='items/c/768.webp', thumb_1600='items/c/1600.webp', is_primary=True,
        )
        second = ItemImage.objects.create(
            item=item, original='items/d/original.webp', thumb_256='items/d/256.webp',
            thumb_768='items/d/768.webp', thumb_1600='items/d/1600.webp', is_primary=False,
        )
        api_client.force_authenticate(user=manager)

        response = api_client.delete(f'/api/v1/items/{item.id}/images/{first.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ItemImage.objects.filter(id=first.id).exists()
        second.refresh_from_db()
        assert second.is_primary is True
        assert ItemImage.objects.filter(item=item, is_primary=True).count() == 1


@pytest.mark.django_db
class TestInactiveReferenceProtection:
    def test_item_cannot_be_created_in_inactive_location(
        self, api_client, manager, location
    ):
        location.is_active = False
        location.save(update_fields=['is_active'])
        api_client.force_authenticate(user=manager)

        response = api_client.post('/api/v1/items/', {
            'name': 'Inactive location item',
            'sku': 'SEM-INACTIVE-LOC',
            'location': location.id,
            'type': 'reusable',
        }, format='json')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert not Item.objects.filter(sku='SEM-INACTIVE-LOC').exists()

    def test_item_cannot_be_moved_to_inactive_category(
        self, api_client, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='SEM-INACTIVE-CAT')
        category = Category.objects.create(name='Inactive semantic category', is_active=False)
        api_client.force_authenticate(user=manager)

        response = api_client.patch(
            f'/api/v1/items/{item.id}/', {'category': category.id}, format='json'
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        item.refresh_from_db()
        assert item.category_id is None


@pytest.mark.django_db
class TestImportSemanticProtection:
    def test_import_type_mismatch_does_not_reinterpret_existing_item(
        self, api_client, admin, manager, warehouse, location
    ):
        item = make_item(owner=manager, location=location, sku='SEM-IMPORT-TYPE', quantity=2)
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Reinterpret,SEM-IMPORT-TYPE,consumable,{warehouse.code},{location.code},,9,pcs,,,\n'
        )

        response = upload_csv(api_client, content)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['error_count'] >= 1
        assert response.data['update_count'] == 0
        item.refresh_from_db()
        assert item.type == ItemType.REUSABLE
        assert item.quantity == 2

    def test_import_cannot_reduce_reusable_quantity_below_active_borrowed(
        self, api_client, admin, manager, borrower, warehouse, location
    ):
        item = make_item(owner=manager, location=location, sku='SEM-IMPORT-BORROWED', quantity=3)
        BorrowRecord.objects.create(
            item=item, borrower=borrower, operator=manager,
            quantity=2, expected_return_date=timezone.localdate() + timedelta(days=2),
            status=BorrowStatus.ACTIVE,
        )
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Too small,SEM-IMPORT-BORROWED,reusable,{warehouse.code},{location.code},,1,pcs,,,\n'
        )

        response = upload_csv(api_client, content)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['error_count'] >= 1
        assert response.data['update_count'] == 0
        item.refresh_from_db()
        assert item.quantity == 3
