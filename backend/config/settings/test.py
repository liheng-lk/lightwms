"""
Test settings for LightWMS project.

IMPORTANT: PostgreSQL is REQUIRED for testing because LightWMS uses:
- pg_trgm extension for fuzzy search
- tsvector/GIN indexes for full-text search  
- Partial unique indexes
- PostgreSQL-specific triggers

To run tests:
1. Start the database:
   docker compose up -d db
   
2. Set DATABASE_URL and run tests:
   export DATABASE_URL=postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test
   pytest
   
   Or use the convenience script:
   ./scripts/test.sh

SQLite is NOT supported for testing this project.
"""
import os
import sys
import dj_database_url
from .base import *

DEBUG = True

# Database configuration
# Priority: DATABASE_URL env var > default PostgreSQL connection
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Use PostgreSQL from DATABASE_URL
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,  # Disable persistent connections for tests
        )
    }
    DATABASES['default'].setdefault('ATOMIC_REQUESTS', False)
    
    # Validate that it's PostgreSQL, not SQLite
    engine = DATABASES['default'].get('ENGINE', '')
    if 'sqlite' in engine.lower():
        print("\n" + "=" * 70, file=sys.stderr)
        print("ERROR: SQLite is NOT supported for LightWMS tests!", file=sys.stderr)
        print("LightWMS requires PostgreSQL for:", file=sys.stderr)
        print("  - pg_trgm extension (fuzzy search)", file=sys.stderr)
        print("  - tsvector/GIN indexes (full-text search)", file=sys.stderr)
        print("  - Partial unique indexes", file=sys.stderr)
        print("  - PostgreSQL-specific triggers", file=sys.stderr)
        print("\nTo run tests:", file=sys.stderr)
        print("  1. docker compose up -d db", file=sys.stderr)
        print("  2. export DATABASE_URL=postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test", file=sys.stderr)
        print("  3. pytest", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)
else:
    # Default PostgreSQL connection for local development
    # Assumes docker-compose db service is running
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'lightwms_test'),
            'USER': os.environ.get('POSTGRES_USER', 'lightwms'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'lightwms_secret'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'ATOMIC_REQUESTS': False,
        }
    }

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Logging: reduce noise in tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
