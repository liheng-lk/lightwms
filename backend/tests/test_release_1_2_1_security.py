"""Regression coverage for the 1.2.1 production-security release."""
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Location, Warehouse
from apps.invoices.models import Invoice
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='security_admin',
        password='StrongPass123!',
        role=UserRole.SUPER_ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username='security_manager',
        password='StrongPass123!',
        role=UserRole.ITEM_MANAGER,
    )


@pytest.fixture
def ordinary(db):
    return User.objects.create_user(
        username='security_user',
        password='StrongPass123!',
        role=UserRole.READ_ONLY_USER,
    )


def create_private_invoice(manager, relative='invoices/2099/01/secure.pdf'):
    invoice = Invoice.objects.create(
        name='安全发票',
        amount=Decimal('88.00'),
        category='采购',
        custom_type='',
        project='',
        file=relative,
        original_filename='安全发票.pdf',
        status='pending',
        item=None,
        registered_month='2099-01',
        created_by=manager,
    )
    path = Path(settings.MEDIA_ROOT) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'%PDF-1.4\nprivate invoice\n%%EOF')
    return invoice, path


@pytest.mark.django_db
class TestPrivateInvoiceMedia:
    def test_registered_invoice_file_requires_management_role(self, manager, ordinary):
        invoice, _ = create_private_invoice(manager)
        url = f'/api/v1/private-media/{invoice.file}'

        anonymous = APIClient().get(url)
        assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED

        ordinary_client = APIClient()
        ordinary_client.force_authenticate(user=ordinary)
        denied = ordinary_client.get(url)
        assert denied.status_code == status.HTTP_403_FORBIDDEN

        manager_client = APIClient()
        manager_client.force_authenticate(user=manager)
        allowed = manager_client.get(url)
        assert allowed.status_code == status.HTTP_200_OK
        assert allowed['Cache-Control'] == 'private, no-store'
        assert allowed['X-Content-Type-Options'] == 'nosniff'
        assert b'%PDF-1.4' in b''.join(allowed.streaming_content)

    def test_invoice_is_not_available_from_public_media_route(self, manager):
        invoice, _ = create_private_invoice(manager, 'invoices/2099/02/not-public.pdf')
        response = APIClient().get(f'/media/{invoice.file}')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_invoice_media_remains_public(self):
        path = Path(settings.MEDIA_ROOT) / 'items' / 'public-smoke.txt'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'public item media')
        response = APIClient().get('/media/items/public-smoke.txt')
        assert response.status_code == status.HTTP_200_OK
        assert b''.join(response.streaming_content) == b'public item media'


@pytest.mark.django_db
def test_disguised_pdf_is_rejected(manager):
    client = APIClient()
    client.force_authenticate(user=manager)
    fake_pdf = SimpleUploadedFile(
        'renamed.pdf',
        b'MZ this is not a PDF',
        content_type='application/pdf',
    )
    response = client.post(
        '/api/v1/invoices/',
        {
            'name': '伪装文件',
            'amount': '1.00',
            'category': '测试',
            'file': fake_pdf,
        },
        format='multipart',
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data['code'] == 'INVALID_FILE_CONTENT'
    assert not Invoice.objects.filter(name='伪装文件').exists()


@pytest.mark.django_db
def test_archived_user_is_anonymized(admin):
    target = User.objects.create_user(
        username='privacy_target',
        password='StrongPass123!',
        role=UserRole.ITEM_MANAGER,
        email='private@example.com',
        phone='18800000001',
        department='Sensitive Department',
        first_name='Private',
        last_name='Person',
        is_staff=True,
        is_superuser=True,
    )
    warehouse = Warehouse.objects.create(code='SEC-WH', name='Security Warehouse')
    Location.objects.create(
        warehouse=warehouse,
        code='SEC-LOC',
        name='Security Location',
        owner=target,
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.delete(f'/api/v1/users/{target.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    archived = User.all_objects.get(pk=target.id)
    assert archived.username.startswith(f'deleted-user-{target.id}-')
    assert archived.email is None
    assert archived.phone is None
    assert archived.department == ''
    assert archived.first_name == ''
    assert archived.last_name == ''
    assert archived.is_active is False
    assert archived.is_staff is False
    assert archived.is_superuser is False
    assert not archived.has_usable_password()

    audit = AuditLog.objects.get(
        action=AuditAction.DELETE,
        target_type=TargetType.USER,
        target_id=target.id,
    )
    assert audit.diff['after']['anonymized'] is True
    assert 'email' not in audit.diff['before']
    assert 'department' not in audit.diff['before']


class BrokenCache:
    def set(self, *args, **kwargs):
        raise RuntimeError('cache unavailable')

    def get(self, *args, **kwargs):
        raise RuntimeError('cache unavailable')

    def delete(self, *args, **kwargs):
        raise RuntimeError('cache unavailable')


@pytest.mark.django_db
def test_health_is_503_when_cache_dependency_is_down(monkeypatch):
    monkeypatch.setattr('core.views.cache', BrokenCache())
    response = APIClient().get('/api/v1/health/')
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data['status'] == 'degraded'
    assert response.data['database'] == 'ok'
    assert response.data['cache'] == 'error'
