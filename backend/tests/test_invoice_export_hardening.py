"""Security and consistency tests for invoice ZIP export."""
import io
import zipfile
from decimal import Decimal
from pathlib import Path, PurePosixPath

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoices.models import Invoice, InvoiceStatus
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='invoice_export_admin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


def create_invoice(*, creator, name, category='采购', file_path=None, amount='10.00'):
    return Invoice.objects.create(
        name=name,
        amount=Decimal(amount),
        category=category,
        custom_type='',
        project='',
        file=file_path or f'invoices/2099/01/{name}.pdf',
        original_filename=f'{name}.pdf',
        status=InvoiceStatus.PENDING,
        item=None,
        registered_month='2099-01',
        created_by=creator,
    )


def materialize(invoice, content=b'%PDF-1.4 invoice'):
    path = Path(settings.MEDIA_ROOT) / invoice.file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.mark.django_db
class TestInvoiceZipExportSafety:
    def test_category_cannot_create_zip_traversal_entry(self, admin):
        invoice = create_invoice(
            creator=admin,
            name='unsafe-category',
            category='../../财务/../外部',
        )
        materialize(invoice)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/export/', {'ids': [invoice.id]}, format='json')

        assert response.status_code == status.HTTP_200_OK
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as archive:
            names = archive.namelist()
        assert len(names) == 1
        entry = PurePosixPath(names[0])
        assert not entry.is_absolute()
        assert '..' not in entry.parts
        assert names[0].count('/') == 1

    def test_exported_file_is_renamed_uploader_name_amount(self, admin):
        invoice = create_invoice(
            creator=admin,
            name='办公用品发票',
            category='采购',
            amount='128.50',
        )
        materialize(invoice)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post('/api/v1/invoices/export/', {'ids': [invoice.id]}, format='json')

        assert response.status_code == status.HTTP_200_OK
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as archive:
            assert archive.namelist() == [
                '采购/invoice_export_admin+办公用品发票+128.50.pdf'
            ]

    def test_duplicate_export_names_get_numeric_suffix(self, admin):
        first = create_invoice(
            creator=admin,
            name='同名发票',
            category='采购',
            amount='10.00',
            file_path='invoices/2099/01/duplicate-a.pdf',
        )
        second = create_invoice(
            creator=admin,
            name='同名发票',
            category='采购',
            amount='10.00',
            file_path='invoices/2099/01/duplicate-b.pdf',
        )
        materialize(first, b'first')
        materialize(second, b'second')
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            '/api/v1/invoices/export/',
            {'ids': [first.id, second.id]},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as archive:
            assert archive.namelist() == [
                '采购/invoice_export_admin+同名发票+10.00.pdf',
                '采购/invoice_export_admin+同名发票+10.00_2.pdf',
            ]

    def test_stored_file_path_cannot_escape_media_root(self, admin):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        outside = media_root.parent / 'invoice-export-outside-secret.pdf'
        outside.write_bytes(b'secret outside media root')
        invoice = create_invoice(
            creator=admin,
            name='unsafe-file-path',
            file_path='../invoice-export-outside-secret.pdf',
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        try:
            response = client.post('/api/v1/invoices/export/', {'ids': [invoice.id]}, format='json')
            assert response.status_code == status.HTTP_409_CONFLICT
            assert response.data['code'] == 'INVALID_FILE_PATH'
        finally:
            outside.unlink(missing_ok=True)

    def test_selected_export_requires_every_requested_id(self, admin):
        invoice = create_invoice(creator=admin, name='strict-selected-export')
        materialize(invoice)
        missing = invoice.id + 99999
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            '/api/v1/invoices/export/',
            {'ids': [invoice.id, missing]},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 'NOT_FOUND'
        assert response.data['details']['ids'] == [missing]

    def test_selected_export_deduplicates_ids(self, admin):
        invoice = create_invoice(creator=admin, name='dedupe-selected-export')
        materialize(invoice)
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(
            '/api/v1/invoices/export/',
            {'ids': [invoice.id, invoice.id]},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as archive:
            assert len(archive.namelist()) == 1
