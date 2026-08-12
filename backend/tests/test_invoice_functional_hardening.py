"""Functional hardening tests for invoice management."""
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.invoices.models import Invoice, InvoiceStatus
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='invoice_func_admin', password='testpass123',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager_a(db):
    return User.objects.create_user(
        username='invoice_func_mgr_a', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def manager_b(db):
    return User.objects.create_user(
        username='invoice_func_mgr_b', password='testpass123',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='invoice_func_user', password='testpass123',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def inventory(db, manager_a, manager_b):
    warehouse = Warehouse.objects.create(
        code='INV-FUNC-WH', name='Invoice Functional Warehouse', is_active=True,
    )
    loc_a = Location.objects.create(
        warehouse=warehouse, code='INV-FUNC-A', name='Invoice A',
        owner=manager_a, is_active=True,
    )
    loc_b = Location.objects.create(
        warehouse=warehouse, code='INV-FUNC-B', name='Invoice B',
        owner=manager_b, is_active=True,
    )
    item_a = Item.objects.create(
        name='Invoice Item A', sku='INV-FUNC-ITEM-A', owner=manager_a,
        location=loc_a, type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=1, is_active=True,
    )
    item_b = Item.objects.create(
        name='Invoice Item B', sku='INV-FUNC-ITEM-B', owner=manager_b,
        location=loc_b, type=ItemType.REUSABLE, status=ItemStatus.AVAILABLE,
        quantity=1, is_active=True,
    )
    return item_a, item_b


def invoice_file(name='invoice.pdf', body=b'%PDF-1.4 test invoice'):
    return SimpleUploadedFile(name, body, content_type='application/pdf')


def create_invoice(client, *, name, amount='123.45', category='采购', item_id=None):
    data = {
        'name': name,
        'amount': amount,
        'category': category,
        'file': invoice_file(f'{name}.pdf'),
    }
    if item_id is not None:
        data['item_id'] = item_id
    return client.post('/api/v1/invoices/', data, format='multipart')


def create_db_invoice(*, creator, name, item=None, status_value=InvoiceStatus.PENDING):
    # File bytes are not needed for status tests; deletion tests create a file.
    return Invoice.objects.create(
        name=name,
        amount=Decimal('10.00'),
        category='采购',
        custom_type='',
        project='',
        file=f'invoices/2099/01/{name}.pdf',
        original_filename=f'{name}.pdf',
        status=status_value,
        item=item,
        registered_month='2099-01',
        created_by=creator,
    )


@pytest.mark.django_db
class TestInvoiceAssociationScope:
    def test_manager_can_attach_invoice_to_owned_item(self, manager_a, inventory):
        item_a, _ = inventory
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = create_invoice(client, name='owned-association', item_id=item_a.id)

        assert response.status_code == status.HTTP_201_CREATED
        invoice = Invoice.objects.get(id=response.data['id'])
        assert invoice.item_id == item_a.id
        assert invoice.created_by_id == manager_a.id

    def test_manager_cannot_attach_invoice_to_other_managers_item(self, manager_a, inventory):
        _, item_b = inventory
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = create_invoice(client, name='cross-association', item_id=item_b.id)

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        assert not Invoice.objects.filter(name='cross-association').exists()

    def test_superadmin_can_attach_invoice_to_any_item(self, admin, inventory):
        _, item_b = inventory
        client = APIClient()
        client.force_authenticate(user=admin)

        response = create_invoice(client, name='admin-association', item_id=item_b.id)

        assert response.status_code == status.HTTP_201_CREATED
        assert Invoice.objects.get(id=response.data['id']).item_id == item_b.id


@pytest.mark.django_db
class TestInvoiceBatchStatusAudit:
    def test_batch_status_requires_every_id_to_exist_and_is_atomic(self, admin):
        first = create_db_invoice(creator=admin, name='batch-status-first')
        second = create_db_invoice(creator=admin, name='batch-status-second')
        missing = max(first.id, second.id) + 99999
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/batch/status/', {
            'ids': [first.id, missing, second.id],
            'status': InvoiceStatus.REIMBURSED,
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.status == InvoiceStatus.PENDING
        assert second.status == InvoiceStatus.PENDING

    def test_batch_status_writes_audit_for_each_invoice(self, admin):
        invoices = [
            create_db_invoice(creator=admin, name=f'batch-status-{i}')
            for i in range(3)
        ]
        ids = [invoice.id for invoice in invoices]
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/batch/status/', {
            'ids': ids,
            'status': InvoiceStatus.REIMBURSED,
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated'] == 3
        for invoice in invoices:
            invoice.refresh_from_db()
            assert invoice.status == InvoiceStatus.REIMBURSED
            assert AuditLog.objects.filter(
                action=AuditAction.UPDATE,
                target_type=TargetType.INVOICE,
                target_id=invoice.id,
                operator=admin,
            ).exists()


@pytest.mark.django_db
class TestInvoiceBatchDeleteLifecycle:
    def _materialize_file(self, invoice, content=b'invoice bytes'):
        path = Path(settings.MEDIA_ROOT) / invoice.file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_batch_delete_missing_id_does_not_delete_files_or_rows(self, admin):
        first = create_db_invoice(creator=admin, name='delete-first')
        second = create_db_invoice(creator=admin, name='delete-second')
        first_path = self._materialize_file(first, b'first')
        second_path = self._materialize_file(second, b'second')
        missing = max(first.id, second.id) + 99999
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/batch/delete/', {
            'ids': [first.id, missing, second.id],
        }, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Invoice.objects.filter(id=first.id).exists()
        assert Invoice.objects.filter(id=second.id).exists()
        assert first_path.exists()
        assert second_path.exists()

    def test_batch_delete_removes_files_and_writes_delete_audit(self, admin):
        invoices = [
            create_db_invoice(creator=admin, name=f'delete-ok-{i}')
            for i in range(2)
        ]
        paths = [self._materialize_file(invoice, f'bytes-{i}'.encode()) for i, invoice in enumerate(invoices)]
        ids = [invoice.id for invoice in invoices]
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/batch/delete/', {
            'ids': ids,
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted'] == 2
        assert not Invoice.objects.filter(id__in=ids).exists()
        assert all(not path.exists() for path in paths)
        for invoice_id in ids:
            assert AuditLog.objects.filter(
                action=AuditAction.DELETE,
                target_type=TargetType.INVOICE,
                target_id=invoice_id,
                operator=admin,
            ).exists()

    def test_batch_delete_duplicate_ids_counts_unique_records(self, admin):
        invoice = create_db_invoice(creator=admin, name='delete-duplicate-id')
        path = self._materialize_file(invoice)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/batch/delete/', {
            'ids': [invoice.id, invoice.id],
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted'] == 1
        assert not Invoice.objects.filter(id=invoice.id).exists()
        assert not path.exists()
