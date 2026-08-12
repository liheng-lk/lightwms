"""Query-efficiency guardrails for borrow-aware inventory read endpoints."""
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import Item, ItemStatus, ItemType, Location, Warehouse
from apps.operations.models import BorrowRecord, BorrowStatus
from apps.users.models import User, UserRole


@pytest.fixture
def dataset(db):
    manager = User.objects.create_user(
        username='query_eff_manager', password='StrongPass123!',
        role=UserRole.ITEM_MANAGER, is_active=True,
    )
    borrower = User.objects.create_user(
        username='query_eff_borrower', password='StrongPass123!',
        role=UserRole.READ_ONLY_USER, is_active=True,
    )
    warehouse = Warehouse.objects.create(
        code='QUERY-EFF-WH', name='Query Efficiency Warehouse', is_active=True,
    )
    location = Location.objects.create(
        warehouse=warehouse, code='QUERY-EFF-LOC', name='Query Efficiency',
        owner=manager, is_active=True,
    )
    due = timezone.localdate() + timedelta(days=7)
    for index in range(20):
        item = Item.objects.create(
            name=f'Query efficiency item {index}', sku=f'QUERY-EFF-{index:03d}',
            location=location, owner=manager, type=ItemType.REUSABLE,
            status=ItemStatus.BORROWED, quantity=1, is_active=True,
        )
        BorrowRecord.objects.create(
            item=item, borrower=borrower, operator=manager,
            quantity=1, expected_return_date=due, status=BorrowStatus.ACTIVE,
        )
    return manager


@pytest.mark.django_db
@pytest.mark.parametrize('path', ['/api/v1/items/', '/api/v1/search/'])
def test_borrow_aware_read_query_count_is_constant_scale(dataset, path):
    client = APIClient()
    client.force_authenticate(user=dataset)

    with CaptureQueriesContext(connection) as captured:
        response = client.get(path, {'page_size': 20})

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 20
    assert len(response.data['results']) == 20
    # Pagination count + item query + images + active borrows plus a small
    # constant amount of framework overhead. A per-item borrower query would
    # push this far above the threshold as the page grows.
    assert len(captured) <= 10
