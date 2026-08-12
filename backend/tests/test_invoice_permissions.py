"""Invoice permission acceptance tests."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.invoices.models import Invoice, InvoiceStatus
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(
        username='invoice_admin', password='StrongPass123!', role=UserRole.SUPER_ADMIN
    )


@pytest.fixture
def manager():
    return User.objects.create_user(
        username='invoice_manager', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def other_manager():
    return User.objects.create_user(
        username='invoice_manager_2', password='StrongPass123!', role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def ordinary():
    return User.objects.create_user(
        username='invoice_user', password='StrongPass123!', role=UserRole.READ_ONLY_USER
    )


def make_invoice(owner, suffix):
    return Invoice.objects.create(
        name=f'Invoice {suffix}',
        amount=Decimal('100.00'),
        category='办公用品',
        file=f'invoices/test-{suffix}.pdf',
        original_filename=f'test-{suffix}.pdf',
        registered_month='2026-08',
        created_by=owner,
    )


@pytest.mark.django_db
class TestInvoicePermissionBoundary:
    def test_ordinary_user_cannot_list_invoices(self, api_client, ordinary):
        api_client.force_authenticate(user=ordinary)
        assert api_client.get('/api/v1/invoices/').status_code == 403

    def test_manager_sees_only_own_invoice_scope(self, api_client, manager, other_manager):
        own = make_invoice(manager, 'own')
        make_invoice(other_manager, 'other')
        api_client.force_authenticate(user=manager)
        response = api_client.get('/api/v1/invoices/')
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        assert [row['id'] for row in results] == [own.id]

    def test_manager_cannot_open_other_managers_invoice(self, api_client, manager, other_manager):
        other = make_invoice(other_manager, 'private')
        api_client.force_authenticate(user=manager)
        assert api_client.get(f'/api/v1/invoices/{other.id}/').status_code == 404

    def test_manager_cannot_change_reimbursement_status(self, api_client, manager):
        invoice = make_invoice(manager, 'status')
        api_client.force_authenticate(user=manager)
        response = api_client.post(
            f'/api/v1/invoices/{invoice.id}/status/',
            {'status': InvoiceStatus.REIMBURSED},
            format='json',
        )
        assert response.status_code == 403

    def test_super_admin_can_see_all_and_change_status(
        self, api_client, admin, manager, other_manager
    ):
        first = make_invoice(manager, 'one')
        make_invoice(other_manager, 'two')
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/v1/invoices/')
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        assert len(results) == 2

        status_response = api_client.post(
            f'/api/v1/invoices/{first.id}/status/',
            {'status': InvoiceStatus.REIMBURSED},
            format='json',
        )
        assert status_response.status_code == 200
        first.refresh_from_db()
        assert first.status == InvoiceStatus.REIMBURSED
