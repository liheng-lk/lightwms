"""Additional invoice permission edge tests."""
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoices.models import Invoice, InvoiceStatus
from apps.users.models import User, UserRole


@pytest.fixture
def manager_a(db):
    return User.objects.create_user(
        username='invoice_edge_manager_a',
        password='StrongPass123!',
        role=UserRole.ITEM_MANAGER,
    )


@pytest.fixture
def manager_b(db):
    return User.objects.create_user(
        username='invoice_edge_manager_b',
        password='StrongPass123!',
        role=UserRole.ITEM_MANAGER,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='invoice_edge_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
    )


def make_invoice(owner, suffix, *, category, month):
    return Invoice.objects.create(
        name=f'Invoice {suffix}',
        amount=Decimal('100.00'),
        category=category,
        file=f'invoices/test-{suffix}.pdf',
        original_filename=f'test-{suffix}.pdf',
        status=InvoiceStatus.PENDING,
        registered_month=month,
        created_by=owner,
    )


@pytest.mark.django_db
class TestInvoiceApprovalBypass:
    def test_manager_cannot_change_status_through_generic_patch(self, manager_a):
        invoice = make_invoice(
            manager_a, 'patch-status', category='办公用品', month='2026-08'
        )
        client = APIClient()
        client.force_authenticate(user=manager_a)
        response = client.patch(
            f'/api/v1/invoices/{invoice.id}/',
            {'status': InvoiceStatus.REIMBURSED}, format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PENDING

    def test_manager_mixed_patch_with_status_is_all_rejected(self, manager_a):
        invoice = make_invoice(
            manager_a, 'mixed-patch', category='办公用品', month='2026-08'
        )
        original_name = invoice.name
        client = APIClient()
        client.force_authenticate(user=manager_a)
        response = client.patch(
            f'/api/v1/invoices/{invoice.id}/',
            {'name': 'Should Not Apply', 'status': InvoiceStatus.REIMBURSED},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        invoice.refresh_from_db()
        assert invoice.name == original_name
        assert invoice.status == InvoiceStatus.PENDING

    def test_superadmin_can_patch_status(self, admin, manager_a):
        invoice = make_invoice(
            manager_a, 'admin-patch-status', category='办公用品', month='2026-08'
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            f'/api/v1/invoices/{invoice.id}/',
            {'status': InvoiceStatus.REIMBURSED}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.REIMBURSED


@pytest.mark.django_db
class TestInvoiceMetadataScope:
    def test_manager_categories_cover_inventory_wide_invoice_values(self, manager_a, manager_b):
        make_invoice(manager_a, 'a-cat', category='A类', month='2026-08')
        make_invoice(manager_b, 'b-cat', category='B类', month='2025-01')
        client = APIClient()
        client.force_authenticate(user=manager_a)
        response = client.get('/api/v1/invoices/categories/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data == ['A类', 'B类']

    def test_manager_months_cover_inventory_wide_invoice_values(self, manager_a, manager_b):
        make_invoice(manager_a, 'a-month', category='A类', month='2026-08')
        make_invoice(manager_b, 'b-month', category='B类', month='2025-01')
        client = APIClient()
        client.force_authenticate(user=manager_a)
        response = client.get('/api/v1/invoices/months/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data == ['2026-08', '2025-01']
