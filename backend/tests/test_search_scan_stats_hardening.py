"""Hardening tests for search, inventory listing, scanner and dashboard counts."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus, TakeRecord
from apps.users.models import User, UserRole


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        username='search_hard_admin', password='StrongPass123!',
        role=UserRole.SUPER_ADMIN, is_active=True,
    )


@pytest.fixture
def manager_a(db):
    return User.objects.create_user(
        username='search_hard_manager_a', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def manager_b(db):
    return User.objects.create_user(
        username='search_hard_manager_b', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )


@pytest.fixture
def borrower_a(db):
    return User.objects.create_user(
        username='search_hard_borrower_a', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def borrower_b(db):
    return User.objects.create_user(
        username='search_hard_borrower_b', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def ordinary_viewer(db):
    return User.objects.create_user(
        username='search_hard_viewer', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(
        code='SEARCH-HARD-WH', name='Search Hardening Warehouse', is_active=True,
    )


@pytest.fixture
def locations(db, warehouse, manager_a, manager_b):
    return (
        Location.objects.create(
            warehouse=warehouse, code='SEARCH-HARD-A', name='Search A',
            owner=manager_a, is_active=True,
        ),
        Location.objects.create(
            warehouse=warehouse, code='SEARCH-HARD-B', name='Search B',
            owner=manager_b, is_active=True,
        ),
    )


@pytest.fixture
def multi_borrow_item(db, locations, manager_a, borrower_a, borrower_b):
    loc_a, _ = locations
    item = Item.objects.create(
        name='Shared Camera Kit', sku='SEARCH-SHARED-001', barcode='SEARCH-BC-001',
        location=loc_a, owner=manager_a, type=ItemType.REUSABLE,
        status=ItemStatus.BORROWED, quantity=2, is_active=True,
    )
    due = timezone.localdate() + timedelta(days=7)
    BorrowRecord.objects.create(
        item=item, borrower=borrower_a, operator=manager_a,
        quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
    )
    BorrowRecord.objects.create(
        item=item, borrower=borrower_b, operator=manager_a,
        quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
    )
    return item


def get_one_result(response, item_id):
    rows = response.data.get('results', response.data)
    return next(row for row in rows if row['id'] == item_id)


@pytest.mark.django_db
class TestSearchInputContract:
    @pytest.mark.parametrize('field,value', [
        ('category', 'not-an-int'),
        ('location', '1.5'),
        ('owner', 'NaN'),
    ])
    def test_non_integer_id_filters_return_400_not_500(self, admin, field, value):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/search/', {field: value})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    @pytest.mark.parametrize('field,value', [
        ('type', 'not-a-real-type'),
        ('status', 'not-a-real-status'),
    ])
    def test_invalid_choice_filters_return_400(self, admin, field, value):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/search/', {field: value})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_keyword_longer_than_contract_is_rejected_not_silently_truncated(self, admin):
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/search/', {'keyword': 'x' * 101})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_page_size_is_capped_at_100(self, admin, locations, manager_a):
        loc_a, _ = locations
        Item.objects.bulk_create([
            Item(
                name=f'Bulk item {i}', sku=f'SEARCH-BULK-{i:03d}', location=loc_a,
                owner=manager_a, type=ItemType.REUSABLE,
                status=ItemStatus.AVAILABLE, quantity=1, is_active=True,
            )
            for i in range(105)
        ])
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/api/v1/search/', {'page_size': 1000})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 105
        assert len(response.data['results']) == 100


@pytest.mark.django_db
class TestBorrowPrivacyAcrossReadEntrypoints:
    @pytest.mark.parametrize('path', ['/api/v1/items/', '/api/v1/search/'])
    def test_unrelated_ordinary_user_cannot_see_borrower_identity(
        self, ordinary_viewer, multi_borrow_item, path,
    ):
        client = APIClient()
        client.force_authenticate(user=ordinary_viewer)

        response = client.get(path, {'keyword': 'SEARCH-SHARED-001', 'page_size': 100})

        assert response.status_code == status.HTTP_200_OK
        row = get_one_result(response, multi_borrow_item.id)
        assert row['current_borrower'] is None
        assert row['current_borrow_record_id'] is None
        assert row.get('active_borrows', []) == []

    @pytest.mark.parametrize('path', ['/api/v1/items/', '/api/v1/search/'])
    def test_ordinary_borrower_sees_only_their_own_active_record(
        self, borrower_a, multi_borrow_item, path,
    ):
        client = APIClient()
        client.force_authenticate(user=borrower_a)

        response = client.get(path, {'keyword': 'SEARCH-SHARED-001', 'page_size': 100})

        assert response.status_code == status.HTTP_200_OK
        row = get_one_result(response, multi_borrow_item.id)
        assert row['current_borrower'] == borrower_a.username
        assert row['current_borrow_record_id'] is not None
        assert len(row['active_borrows']) == 1
        assert row['active_borrows'][0]['borrower'] == borrower_a.id

    @pytest.mark.parametrize('path', ['/api/v1/items/', '/api/v1/search/'])
    def test_owner_manager_sees_all_active_records_without_fake_singular_borrower(
        self, manager_a, multi_borrow_item, path,
    ):
        client = APIClient()
        client.force_authenticate(user=manager_a)

        response = client.get(path, {'keyword': 'SEARCH-SHARED-001', 'page_size': 100})

        assert response.status_code == status.HTTP_200_OK
        row = get_one_result(response, multi_borrow_item.id)
        assert row['current_borrower'] is None
        assert row['current_borrow_record_id'] is None
        assert len(row['active_borrows']) == 2

    def test_scanner_keeps_same_ordinary_privacy_contract(
        self, ordinary_viewer, multi_borrow_item,
    ):
        client = APIClient()
        client.force_authenticate(user=ordinary_viewer)

        response = client.get(f'/api/v1/items/by-barcode/{multi_borrow_item.barcode}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['active_borrows'] == []
        assert response.data['borrowed_quantity'] == 2
        assert response.data['available_quantity'] == 0


@pytest.mark.django_db
class TestRoleScopedDashboardCounts:
    def test_manager_dashboard_source_counts_do_not_include_other_manager_scope(
        self, manager_a, manager_b, locations, borrower_a, borrower_b,
    ):
        loc_a, loc_b = locations
        reusable_a = Item.objects.create(
            name='Manager A reusable', sku='DASH-A-REUSE', location=loc_a,
            owner=manager_a, type=ItemType.REUSABLE, status=ItemStatus.BORROWED,
            quantity=1, is_active=True,
        )
        reusable_b = Item.objects.create(
            name='Manager B reusable', sku='DASH-B-REUSE', location=loc_b,
            owner=manager_b, type=ItemType.REUSABLE, status=ItemStatus.BORROWED,
            quantity=1, is_active=True,
        )
        consumable_a = Item.objects.create(
            name='Manager A consumable', sku='DASH-A-CONS', location=loc_a,
            owner=manager_a, type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
            quantity=9, is_active=True,
        )
        consumable_b = Item.objects.create(
            name='Manager B consumable', sku='DASH-B-CONS', location=loc_b,
            owner=manager_b, type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
            quantity=9, is_active=True,
        )
        due = timezone.localdate() + timedelta(days=3)
        BorrowRecord.objects.create(
            item=reusable_a, borrower=borrower_a, operator=manager_a,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
        BorrowRecord.objects.create(
            item=reusable_b, borrower=borrower_b, operator=manager_b,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
        TakeRecord.objects.create(
            item=consumable_a, taker=borrower_a, operator=manager_a, quantity=1,
        )
        TakeRecord.objects.create(
            item=consumable_b, taker=borrower_b, operator=manager_b, quantity=1,
        )
        client = APIClient()
        client.force_authenticate(user=manager_a)
        today = timezone.localdate().isoformat()

        item_response = client.get('/api/v1/items/', {'page_size': 1})
        borrow_response = client.get('/api/v1/borrow-records/', {'status': 'active', 'page_size': 1})
        take_response = client.get(
            '/api/v1/take-records/',
            {'start_date': today, 'end_date': today, 'page_size': 1},
        )

        assert item_response.status_code == status.HTTP_200_OK
        assert borrow_response.status_code == status.HTTP_200_OK
        assert take_response.status_code == status.HTTP_200_OK
        assert item_response.data['count'] == 2
        assert borrow_response.data['count'] == 1
        assert take_response.data['count'] == 1

    def test_ordinary_dashboard_borrow_and_take_counts_are_self_only(
        self, ordinary_viewer, borrower_a, manager_a, locations,
    ):
        loc_a, _ = locations
        reusable = Item.objects.create(
            name='Ordinary dashboard reusable', sku='DASH-ORD-REUSE', location=loc_a,
            owner=manager_a, type=ItemType.REUSABLE, status=ItemStatus.BORROWED,
            quantity=2, is_active=True,
        )
        consumable = Item.objects.create(
            name='Ordinary dashboard consumable', sku='DASH-ORD-CONS', location=loc_a,
            owner=manager_a, type=ItemType.CONSUMABLE, status=ItemStatus.IN_STOCK,
            quantity=9, is_active=True,
        )
        due = timezone.localdate() + timedelta(days=3)
        BorrowRecord.objects.create(
            item=reusable, borrower=ordinary_viewer, operator=manager_a,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
        BorrowRecord.objects.create(
            item=reusable, borrower=borrower_a, operator=manager_a,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
        TakeRecord.objects.create(
            item=consumable, taker=ordinary_viewer, operator=manager_a, quantity=1,
        )
        TakeRecord.objects.create(
            item=consumable, taker=borrower_a, operator=manager_a, quantity=1,
        )
        client = APIClient()
        client.force_authenticate(user=ordinary_viewer)
        today = timezone.localdate().isoformat()

        borrow_response = client.get('/api/v1/borrow-records/', {'status': 'active', 'page_size': 1})
        take_response = client.get(
            '/api/v1/take-records/',
            {'start_date': today, 'end_date': today, 'page_size': 1},
        )

        assert borrow_response.status_code == status.HTTP_200_OK
        assert take_response.status_code == status.HTTP_200_OK
        assert borrow_response.data['count'] == 1
        assert take_response.data['count'] == 1
