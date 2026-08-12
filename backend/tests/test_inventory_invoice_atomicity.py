"""Atomicity tests for item creation with invoice upload."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, Location, Warehouse
from apps.users.models import User, UserRole


@pytest.mark.django_db
def test_invalid_invoice_file_rolls_back_created_item():
    client = APIClient()
    manager = User.objects.create_user(
        username='invoice_atomic_manager',
        password='testpass123',
        role=UserRole.ITEM_MANAGER,
        is_active=True,
    )
    warehouse = Warehouse.objects.create(
        code='INV-ATOMIC-WH', name='Invoice Atomic Warehouse', is_active=True
    )
    location = Location.objects.create(
        warehouse=warehouse,
        code='INV-ATOMIC-LOC',
        name='Invoice Atomic Location',
        owner=manager,
        is_active=True,
    )
    client.force_authenticate(user=manager)

    invalid_invoice = SimpleUploadedFile(
        'invoice.txt', b'not-an-allowed-invoice', content_type='text/plain'
    )
    response = client.post('/api/v1/items/with-invoice/', {
        'name': 'Atomic invoice item',
        'sku': 'INV-ATOMIC-001',
        'location': location.id,
        'type': 'reusable',
        'quantity': 1,
        'invoice_file': invalid_invoice,
        'invoice_amount': '123.45',
        'invoice_category': '采购',
    }, format='multipart')

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data['code'] == 'INVALID_FILE_TYPE'
    assert not Item.objects.filter(sku='INV-ATOMIC-001').exists()
