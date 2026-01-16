"""
Search service for LightWMS.

This module implements the search functionality for items using:
- PostgreSQL full-text search (tsvector + GIN index)
- pg_trgm for fuzzy matching
- Multi-priority ranking system

Search ranking priority:
1. Exact SKU match (case-insensitive) - highest priority
2. SKU prefix match
3. Name FTS rank
4. Barcode match
5. Trigram similarity - lowest priority

With deterministic tie-breaker: updated_at desc, id desc
"""
from dataclasses import dataclass
from typing import Optional

from django.db.models import Case, When, Value, F, Q, QuerySet, FloatField

from apps.inventory.models import Item
from core.db_utils import is_postgres


# Constants for keyword validation
MIN_KEYWORD_LENGTH = 1
MAX_KEYWORD_LENGTH = 100


@dataclass
class SearchFilters:
    """Data class for search filters."""
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: Optional[str] = None
    type: Optional[str] = None


class SearchService:
    """
    Service for searching items with FTS and trigram support.
    
    Implements Requirements 11.1-11.11:
    - Full-text search using tsvector + GIN index
    - Trigram similarity for fuzzy matching
    - Multi-priority ranking system
    - Filter support (category, location, owner, status, type)
    - include_inactive parameter for Super_Admin
    - Deterministic tie-breaker ordering
    """
    
    @staticmethod
    def _preprocess_keyword(keyword: Optional[str]) -> Optional[str]:
        """
        Preprocess keyword for search.
        
        - Strip whitespace
        - Enforce length limits (1-100 characters)
        - Return None for empty strings
        
        Args:
            keyword: Raw keyword input
            
        Returns:
            Preprocessed keyword or None if invalid/empty
        """
        if keyword is None:
            return None
        
        # Strip whitespace
        keyword = keyword.strip()
        
        # Empty string after strip -> return None
        if not keyword:
            return None
        
        # Enforce length limits
        if len(keyword) < MIN_KEYWORD_LENGTH:
            return None
        
        if len(keyword) > MAX_KEYWORD_LENGTH:
            keyword = keyword[:MAX_KEYWORD_LENGTH]
        
        return keyword
    
    @staticmethod
    def _search_postgres(
        qs: QuerySet,
        keyword: str,
    ) -> QuerySet:
        """
        PostgreSQL-specific search with FTS and trigram.
        
        Uses:
        - SearchQuery with @@ operator for GIN index
        - SearchRank for FTS ranking
        - TrigramSimilarity for fuzzy matching
        """
        from django.contrib.postgres.search import SearchRank, SearchQuery, TrigramSimilarity
        
        # Build SearchQuery for FTS (uses @@ operator with GIN index)
        search_query = SearchQuery(keyword, search_type='plain')
        
        qs = qs.annotate(
            # Priority 1: Exact SKU match (score: 100)
            exact_sku=Case(
                When(sku__iexact=keyword, then=Value(100.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 2: SKU prefix match (score: 80)
            prefix_sku=Case(
                When(sku__istartswith=keyword, then=Value(80.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 3: FTS rank (score: 0-60)
            # SearchRank returns 0-1, multiply by 60 for priority weighting
            fts_rank=SearchRank(F('search_vector'), search_query) * 60,
            # Priority 4: Barcode match (score: 40)
            barcode_match=Case(
                When(barcode__iexact=keyword, then=Value(40.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 5: Trigram similarity (score: 0-20)
            # TrigramSimilarity returns 0-1, multiply by 20 for priority weighting
            trgm_score=TrigramSimilarity('name', keyword) * 20,
            # Combined rank score
            rank_score=(
                F('exact_sku') + F('prefix_sku') + F('fts_rank') +
                F('barcode_match') + F('trgm_score')
            )
        ).filter(
            # Match at least one condition
            # Use SearchQuery for FTS to ensure @@ operator is used
            Q(sku__icontains=keyword) |
            Q(name__icontains=keyword) |
            Q(barcode__icontains=keyword) |
            Q(search_vector=search_query)
        ).order_by(
            '-rank_score',      # Primary: relevance score
            '-updated_at',      # Tie-breaker 1: most recently updated
            '-id'               # Tie-breaker 2: newest ID
        )
        
        return qs
    
    @staticmethod
    def _search_fallback(
        qs: QuerySet,
        keyword: str,
    ) -> QuerySet:
        """
        Fallback search for non-PostgreSQL databases (e.g., SQLite for testing).
        
        Uses simple LIKE queries without FTS or trigram.
        """
        qs = qs.annotate(
            # Priority 1: Exact SKU match (score: 100)
            exact_sku=Case(
                When(sku__iexact=keyword, then=Value(100.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 2: SKU prefix match (score: 80)
            prefix_sku=Case(
                When(sku__istartswith=keyword, then=Value(80.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 3: Name contains (score: 60 for simplicity)
            name_match=Case(
                When(name__icontains=keyword, then=Value(60.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Priority 4: Barcode match (score: 40)
            barcode_match=Case(
                When(barcode__iexact=keyword, then=Value(40.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            # Combined rank score
            rank_score=(
                F('exact_sku') + F('prefix_sku') + F('name_match') +
                F('barcode_match')
            )
        ).filter(
            # Match at least one condition
            Q(sku__icontains=keyword) |
            Q(name__icontains=keyword) |
            Q(barcode__icontains=keyword)
        ).order_by(
            '-rank_score',      # Primary: relevance score
            '-updated_at',      # Tie-breaker 1: most recently updated
            '-id'               # Tie-breaker 2: newest ID
        )
        
        return qs
    
    @staticmethod
    def search(
        keyword: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
        user=None,
        include_inactive: bool = False,
    ) -> QuerySet:
        """
        Search items with keyword and filters.
        
        Args:
            keyword: Search keyword (optional)
            filters: SearchFilters object with filter criteria
            user: Current user for data isolation
            include_inactive: Include inactive items (Super_Admin only)
            
        Returns:
            QuerySet of matching items, ordered by relevance
            
        Implements:
            - Requirement 11.1: Keyword search against name, sku, barcode
            - Requirement 11.4: Ranking priority
            - Requirement 11.5: Filter support
            - Requirement 11.10: Inactive exclusion by default
            - Requirement 11.11: Deterministic tie-breaker
        """
        # Base queryset with related objects
        qs = Item.objects.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )
        
        # Check user role using model properties (not string comparison)
        user_is_super_admin = user and getattr(user, 'is_super_admin', False)
        
        # Default filter: exclude inactive items
        # Only Super_Admin can include inactive items
        if not include_inactive or not user_is_super_admin:
            qs = qs.filter(is_active=True)
        
        # Item_Manager can see all items (no data isolation)
        
        # Apply filters
        if filters:
            if filters.category_id is not None:
                qs = qs.filter(category_id=filters.category_id)
            if filters.location_id is not None:
                qs = qs.filter(location_id=filters.location_id)
            if filters.owner_id is not None:
                # Only Super_Admin can filter by owner
                if user_is_super_admin:
                    qs = qs.filter(owner_id=filters.owner_id)
            if filters.status:
                qs = qs.filter(status=filters.status)
            if filters.type:
                qs = qs.filter(type=filters.type)
        
        # Preprocess keyword
        keyword = SearchService._preprocess_keyword(keyword)
        
        # Keyword search with ranking
        if keyword:
            # Use queryset.db to get the correct database alias
            if is_postgres(qs.db):
                qs = SearchService._search_postgres(qs, keyword)
            else:
                qs = SearchService._search_fallback(qs, keyword)
        else:
            # No keyword: default ordering with tie-breaker
            qs = qs.order_by('-updated_at', '-id')
        
        return qs
