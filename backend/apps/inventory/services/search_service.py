"""
Search service for LightWMS.

This module implements the search functionality for items using:
- PostgreSQL full-text search (tsvector + GIN index)
- pg_trgm for fuzzy matching
- Multi-priority ranking system
"""
from dataclasses import dataclass
from typing import Optional

from django.db.models import Case, When, Value, F, Q, QuerySet, FloatField

from apps.inventory.models import Item
from core.db_utils import is_postgres
from core.role_utils import is_super_admin, is_item_manager


MIN_KEYWORD_LENGTH = 1
MAX_KEYWORD_LENGTH = 100


@dataclass
class SearchFilters:
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: Optional[str] = None
    type: Optional[str] = None


class SearchService:
    """Search items with ranking, filters and role-aware visibility."""

    @staticmethod
    def _preprocess_keyword(keyword: Optional[str]) -> Optional[str]:
        if keyword is None:
            return None
        keyword = keyword.strip()
        if not keyword:
            return None
        if len(keyword) > MAX_KEYWORD_LENGTH:
            keyword = keyword[:MAX_KEYWORD_LENGTH]
        return keyword

    @staticmethod
    def _search_postgres(qs: QuerySet, keyword: str) -> QuerySet:
        from django.contrib.postgres.search import SearchRank, SearchQuery, TrigramSimilarity

        search_query = SearchQuery(keyword, search_type='plain')
        return qs.annotate(
            exact_sku=Case(
                When(sku__iexact=keyword, then=Value(100.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            prefix_sku=Case(
                When(sku__istartswith=keyword, then=Value(80.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            fts_rank=SearchRank(F('search_vector'), search_query) * 60,
            barcode_match=Case(
                When(barcode__iexact=keyword, then=Value(40.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            trgm_score=TrigramSimilarity('name', keyword) * 20,
            rank_score=(
                F('exact_sku') + F('prefix_sku') + F('fts_rank') +
                F('barcode_match') + F('trgm_score')
            )
        ).filter(
            Q(sku__icontains=keyword) |
            Q(name__icontains=keyword) |
            Q(barcode__icontains=keyword) |
            Q(search_vector=search_query)
        ).order_by('-rank_score', '-updated_at', '-id')

    @staticmethod
    def _search_fallback(qs: QuerySet, keyword: str) -> QuerySet:
        return qs.annotate(
            exact_sku=Case(
                When(sku__iexact=keyword, then=Value(100.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            prefix_sku=Case(
                When(sku__istartswith=keyword, then=Value(80.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            name_match=Case(
                When(name__icontains=keyword, then=Value(60.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            barcode_match=Case(
                When(barcode__iexact=keyword, then=Value(40.0)),
                default=Value(0.0), output_field=FloatField()
            ),
            rank_score=(
                F('exact_sku') + F('prefix_sku') + F('name_match') +
                F('barcode_match')
            )
        ).filter(
            Q(sku__icontains=keyword) |
            Q(name__icontains=keyword) |
            Q(barcode__icontains=keyword)
        ).order_by('-rank_score', '-updated_at', '-id')

    @staticmethod
    def search(
        keyword: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
        user=None,
        include_inactive: bool = False,
    ) -> QuerySet:
        qs = Item.objects.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )

        user_is_super_admin = is_super_admin(user)
        user_is_item_manager = is_item_manager(user)

        # Inactive inventory is maintenance data and remains Super Admin only.
        if not include_inactive or not user_is_super_admin:
            qs = qs.filter(is_active=True)

        # Item Manager is a global inventory-business role. ``owner`` is
        # responsibility metadata and can be used as a filter, not visibility
        # isolation. Ordinary users can also search all active stock read-only.
        if filters:
            if filters.category_id is not None:
                qs = qs.filter(category_id=filters.category_id)
            if filters.location_id is not None:
                qs = qs.filter(location_id=filters.location_id)
            if filters.owner_id is not None and (user_is_super_admin or user_is_item_manager):
                qs = qs.filter(owner_id=filters.owner_id)
            if filters.status:
                qs = qs.filter(status=filters.status)
            if filters.type:
                qs = qs.filter(type=filters.type)

        keyword = SearchService._preprocess_keyword(keyword)
        if keyword:
            if is_postgres(qs.db):
                qs = SearchService._search_postgres(qs, keyword)
            else:
                qs = SearchService._search_fallback(qs, keyword)
        else:
            qs = qs.order_by('-updated_at', '-id')

        return qs
