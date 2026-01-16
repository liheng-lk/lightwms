"""
Pytest configuration and fixtures for LightWMS tests.

IMPORTANT: PostgreSQL is REQUIRED for testing this project.
SQLite is NOT supported due to PostgreSQL-specific features:
- pg_trgm extension for fuzzy search
- tsvector/GIN indexes for full-text search
- Partial unique indexes
- PostgreSQL-specific triggers

Usage:
    # Start the database
    docker-compose up -d db
    
    # Run tests (uses default PostgreSQL connection)
    pytest
    
    # Or specify DATABASE_URL explicitly
    export DATABASE_URL=postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test
    pytest
"""
import pytest
from django.db import connections


def pytest_configure(config):
    """
    Verify PostgreSQL is being used before running tests.
    """
    # Force Django to set up the database connection
    from django.conf import settings
    
    # Check if we're using PostgreSQL
    db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'postgresql' not in db_engine:
        raise pytest.UsageError(
            "\n\n"
            "=" * 70 + "\n"
            "ERROR: PostgreSQL is REQUIRED for testing LightWMS.\n"
            "=" * 70 + "\n\n"
            "This project uses PostgreSQL-specific features:\n"
            "  - pg_trgm extension for fuzzy search\n"
            "  - tsvector/GIN indexes for full-text search\n"
            "  - Partial unique indexes\n"
            "  - PostgreSQL-specific triggers\n\n"
            "To run tests:\n"
            "  1. Start PostgreSQL: docker-compose up -d db\n"
            "  2. Run tests: pytest\n\n"
            "Or set DATABASE_URL:\n"
            "  export DATABASE_URL=postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test\n"
            "  pytest\n"
            "=" * 70 + "\n"
        )


@pytest.fixture(scope='session')
def is_postgres_db():
    """
    Check if the test database is PostgreSQL.
    
    Returns:
        bool: True if PostgreSQL, False otherwise
    """
    return connections['default'].vendor == 'postgresql'


@pytest.fixture(autouse=True)
def verify_postgres(is_postgres_db):
    """
    Verify PostgreSQL is being used for all tests.
    """
    if not is_postgres_db:
        pytest.fail(
            "PostgreSQL is required for testing. "
            "Please set DATABASE_URL or start docker-compose db service."
        )
