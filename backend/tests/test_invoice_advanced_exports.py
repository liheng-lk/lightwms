"""Regression tests for invoice uploader/date filters and reimbursement Excel export."""
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.invoices.models import Invoice, InvoiceStatus
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='invoice_filter_admin',
        password='testpass123',
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )


@pytest.fixture
def uploader(db):
    return User.objects.create_user(
        username='invoice_uploader',
        password='testpass123',
        role=UserRole.ITEM_MANAGER,
        is_active=True,
    )


def create_invoice(*, creator, name, amount='10.00'):
    return Invoice.objects.create(
        name=name,
        amount=Decimal(amount),
        category='采购',
        custom_type='办公用品',
        project='仓库升级',
        file=f'invoices/2099/01/{name}.pdf',
        original_filename=f'{name}.pdf',
        status=InvoiceStatus.PENDING,
        item=None,
        registered_month='2099-01',
        created_by=creator,
    )


@pytest.mark.django_db
class TestAdvancedInvoiceFiltersAndExports:
    def test_list_can_filter_by_uploader(self, admin, uploader):
        own = create_invoice(creator=admin, name='admin-invoice')
        uploaded = create_invoice(creator=uploader, name='uploader-invoice')
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(f'/api/v1/invoices/?uploader={uploader.id}')

        assert response.status_code == 200
        ids = [row['id'] for row in response.data['results']]
        assert ids == [uploaded.id]
        assert own.id not in ids

    def test_list_can_filter_by_custom_date_range(self, admin):
        old_invoice = create_invoice(creator=admin, name='old-invoice')
        recent_invoice = create_invoice(creator=admin, name='recent-invoice')
        Invoice.objects.filter(pk=old_invoice.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        date_from = (timezone.localdate() - timedelta(days=1)).isoformat()
        date_to = timezone.localdate().isoformat()

        response = client.get(
            f'/api/v1/invoices/?date_from={date_from}&date_to={date_to}'
        )

        assert response.status_code == 200
        ids = [row['id'] for row in response.data['results']]
        assert recent_invoice.id in ids
        assert old_invoice.id not in ids

    def test_reimbursement_excel_respects_uploader_and_contains_total(self, admin, uploader):
        create_invoice(creator=admin, name='excluded', amount='99.00')
        first = create_invoice(creator=uploader, name='included-1', amount='12.50')
        second = create_invoice(creator=uploader, name='included-2', amount='7.50')
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(
            f'/api/v1/invoices/export/reimbursement/?uploader={uploader.id}'
        )

        assert response.status_code == 200
        assert response['Content-Type'].startswith(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        workbook = load_workbook(io.BytesIO(response.content), data_only=True)
        sheet = workbook['报销清单']
        assert sheet['J2'].value == uploader.username
        names = {sheet['B2'].value, sheet['B3'].value}
        assert names == {first.name, second.name}
        assert sheet['A4'].value == '合计'
        assert sheet['C4'].value == 20

    def test_invalid_date_range_returns_400(self, admin):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(
            '/api/v1/invoices/export/reimbursement/?date_from=2026-08-20&date_to=2026-08-01'
        )

        assert response.status_code == 400
        assert response.data['code'] == 'INVALID_FILTER'
