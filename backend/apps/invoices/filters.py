"""Shared invoice filtering for list and export endpoints."""
from __future__ import annotations

from datetime import date

from .services import InvoiceService


class InvoiceFilterError(ValueError):
    """Raised when an invoice filter query parameter is invalid."""


def _parse_date(value: str | None, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InvoiceFilterError(f'{field_name} 必须使用 YYYY-MM-DD 格式') from exc


def _parse_optional_int(value: str | None, field_name: str) -> int | None:
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InvoiceFilterError(f'{field_name} 必须是有效的整数 ID') from exc
    if parsed <= 0:
        raise InvoiceFilterError(f'{field_name} 必须大于 0')
    return parsed


def get_filtered_invoices(query_params):
    """Return one QuerySet for UI lists, ZIP exports and XLSX exports."""
    date_from = _parse_date(query_params.get('date_from'), 'date_from')
    date_to = _parse_date(query_params.get('date_to'), 'date_to')
    if date_from and date_to and date_from > date_to:
        raise InvoiceFilterError('开始日期不能晚于结束日期')

    uploader_id = _parse_optional_int(
        query_params.get('uploader') or query_params.get('created_by'),
        'uploader',
    )
    item_id = _parse_optional_int(query_params.get('item'), 'item')

    invoices = InvoiceService.list(
        category=query_params.get('category'),
        status=query_params.get('status'),
        registered_month=query_params.get('month'),
        item_id=item_id,
        created_by_id=uploader_id,
        search=query_params.get('search'),
    )

    if date_from:
        invoices = invoices.filter(created_at__date__gte=date_from)
    if date_to:
        invoices = invoices.filter(created_at__date__lte=date_to)
    return invoices
