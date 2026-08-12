"""Edge-case regression tests for inventory visibility and bulk semantics."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemImage, ItemStatus, ItemType, Location, Warehouse
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
        username='edge_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='edge_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def other_manager(db):
    return User.objects.create_user(
        username='edge_other_manager', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='edge_ordinary', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(code='EDGE-WH', name='Edge Warehouse', is_active=True)


@pytest.fixture
def location(db, warehouse, manager):
    return Location.objects.create(
        warehouse=warehouse, code='EDGE-LOC', name='Edge Location',
        owner=manager, is_active=True,
    )


def make_item(*, owner, location, sku, active=True, barcode=None):
    return Item.objects.create(
        name=sku, sku=sku, barcode=barcode, owner=owner, location=location,
        type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=1, is_active=active,
    )


@pytest.mark.django_db
class TestInactiveItemVisibility:
    def test_ordinary_user_cannot_open_inactive_item_by_known_id(
        self, api_client, ordinary, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='INACTIVE-DIRECT-001', active=False)
        api_client.force_authenticate(user=ordinary)

        response = api_client.get(f'/api/v1/items/{item.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_ordinary_user_cannot_list_images_for_inactive_item(
        self, api_client, ordinary, manager, location
    ):
        item = make_item(owner=manager, location=location, sku='INACTIVE-IMAGE-001', active=False)
        ItemImage.objects.create(
            item=item,
            original='items/inactive/original.webp',
            thumb_256='items/inactive/256.webp',
            thumb_768='items/inactive/768.webp',
            thumb_1600='items/inactive/1600.webp',
            is_primary=True,
        )
        api_client.force_authenticate(user=ordinary)

        response = api_client.get(f'/api/v1/items/{item.id}/images/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBatchOwnerCompleteness:
    def test_batch_owner_change_rejects_missing_item_id_without_partial_update(
        self, api_client, admin, manager, other_manager, location
    ):
        item = make_item(owner=manager, location=location, sku='OWNER-BATCH-001')
        missing_id = item.id + 99999
        api_client.force_authenticate(user=admin)

        response = api_client.post('/api/v1/items/batch-update-owner/', {
            'item_ids': [item.id, missing_id],
            'owner_id': other_manager.id,
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        item.refresh_from_db()
        assert item.owner_id == manager.id


@pytest.mark.django_db
class TestImportAllOrNothingMode:
    def test_allow_partial_false_rolls_back_runtime_row_failure(
        self, api_client, admin, manager, warehouse, location
    ):
        make_item(
            owner=manager, location=location, sku='EDGE-EXISTING-BARCODE',
            barcode='EDGE-DUP-BARCODE',
        )
        api_client.force_authenticate(user=admin)
        content = HEADERS + (
            f'Valid first,EDGE-VALID-FIRST,reusable,{warehouse.code},{location.code},,2,pcs,,,\n'
            f'Duplicate second,EDGE-DUP-SECOND,reusable,{warehouse.code},{location.code},EDGE-DUP-BARCODE,1,pcs,,,\n'
        )
        upload = SimpleUploadedFile('items.csv', content.encode('utf-8'), content_type='text/csv')

        response = api_client.post(
            '/api/v1/items/import/',
            {'file': upload, 'allow_partial': 'false'},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['error_count'] >= 1
        assert response.data['create_count'] == 0
        assert not Item.objects.filter(sku='EDGE-VALID-FIRST').exists()
        assert not Item.objects.filter(sku='EDGE-DUP-SECOND').exists()
