"""
Database utility functions for LightWMS.

This module provides stable database vendor detection that works correctly
across different contexts (migrations, services, tests, multi-DB setups).

IMPORTANT: Never use `django.db.connection.vendor` directly as it can be
unreliable in pytest/multi-DB/lazy connection scenarios.
"""
from django.db import connections


def is_postgres(using: str = "default") -> bool:
    """
    Check if the specified database connection is PostgreSQL.
    
    This function uses `connections[using].vendor` which is more reliable
    than `connection.vendor` in multi-DB and test scenarios.
    
    Args:
        using: Database alias to check (default: "default")
        
    Returns:
        True if the database is PostgreSQL, False otherwise
        
    Usage in services:
        from core.db_utils import is_postgres
        
        # Check default database
        if is_postgres():
            # PostgreSQL-specific code
            
        # Check specific database alias
        if is_postgres("replica"):
            # PostgreSQL-specific code for replica
            
    Usage with QuerySet:
        from core.db_utils import is_postgres
        
        def search(self, queryset):
            # Use queryset.db to get the database alias
            if is_postgres(queryset.db):
                return self._search_postgres(queryset)
            return self._search_fallback(queryset)
    """
    return connections[using].vendor == "postgresql"


def is_postgres_for_schema_editor(schema_editor) -> bool:
    """
    Check if the schema editor's connection is PostgreSQL.
    
    This function should be used in Django migrations to ensure
    PostgreSQL-specific SQL is only executed on PostgreSQL databases.
    
    Args:
        schema_editor: Django schema editor instance
        
    Returns:
        True if the database is PostgreSQL, False otherwise
        
    Usage in migrations:
        from core.db_utils import is_postgres_for_schema_editor
        
        def forwards(apps, schema_editor):
            if not is_postgres_for_schema_editor(schema_editor):
                return  # Skip on non-PostgreSQL databases
            schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    """
    return schema_editor.connection.vendor == "postgresql"
