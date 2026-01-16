"""
Migration for creating search-related indexes and triggers for Item model.

Creates:
- search_vector update trigger (automatically updates on INSERT/UPDATE)
- GIN index on search_vector for full-text search
- pg_trgm GIN indexes on sku, name, barcode for fuzzy matching

Note: These operations are PostgreSQL-specific and will be skipped on other databases.
"""
from django.db import migrations


def create_pg_trgm_extension(apps, schema_editor):
    """Create pg_trgm extension if on PostgreSQL.
    
    Note: This requires superuser privileges or the extension must be
    pre-installed by a DBA. If you're using a managed PostgreSQL service,
    you may need to enable pg_trgm through the service's admin console.
    """
    if schema_editor.connection.vendor != 'postgresql':
        return
    try:
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception as e:
        error_msg = str(e).lower()
        if 'permission denied' in error_msg or 'must be owner' in error_msg:
            raise RuntimeError(
                "\n" + "=" * 70 + "\n"
                "ERROR: Cannot create pg_trgm extension - permission denied.\n\n"
                "LightWMS requires the pg_trgm extension for fuzzy search.\n"
                "Please ask your DBA to run:\n"
                "  CREATE EXTENSION IF NOT EXISTS pg_trgm;\n\n"
                "Or if using a managed PostgreSQL service, enable pg_trgm\n"
                "through the service's admin console.\n"
                + "=" * 70
            ) from e
        raise


def create_search_vector_function(apps, schema_editor):
    """Create search vector update function if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION update_item_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('simple', COALESCE(NEW.sku, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.barcode, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def drop_search_vector_function(apps, schema_editor):
    """Drop search vector update function if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP FUNCTION IF EXISTS update_item_search_vector();")


def create_search_vector_trigger(apps, schema_editor):
    """Create search vector trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS trg_item_search_vector ON inventory_item;
        CREATE TRIGGER trg_item_search_vector
            BEFORE INSERT OR UPDATE ON inventory_item
            FOR EACH ROW
            EXECUTE FUNCTION update_item_search_vector();
    """)


def drop_search_vector_trigger(apps, schema_editor):
    """Drop search vector trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS trg_item_search_vector ON inventory_item;")


def create_search_indexes(apps, schema_editor):
    """Create search indexes if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    # GIN index on search_vector
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS idx_item_search_vector 
        ON inventory_item 
        USING GIN (search_vector);
    """)
    
    # pg_trgm GIN indexes
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS idx_item_sku_trgm 
        ON inventory_item 
        USING GIN (sku gin_trgm_ops);
    """)
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS idx_item_name_trgm 
        ON inventory_item 
        USING GIN (name gin_trgm_ops);
    """)
    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS idx_item_barcode_trgm 
        ON inventory_item 
        USING GIN (barcode gin_trgm_ops)
        WHERE barcode IS NOT NULL;
    """)


def drop_search_indexes(apps, schema_editor):
    """Drop search indexes if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS idx_item_search_vector;")
    schema_editor.execute("DROP INDEX IF EXISTS idx_item_sku_trgm;")
    schema_editor.execute("DROP INDEX IF EXISTS idx_item_name_trgm;")
    schema_editor.execute("DROP INDEX IF EXISTS idx_item_barcode_trgm;")


def update_existing_search_vectors(apps, schema_editor):
    """Update search vectors for existing items if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        UPDATE inventory_item 
        SET search_vector = 
            setweight(to_tsvector('simple', COALESCE(sku, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(name, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(barcode, '')), 'C');
    """)


def noop(apps, schema_editor):
    """No-op function for reverse migrations."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_create_item'),
    ]

    operations = [
        # Enable pg_trgm extension
        migrations.RunPython(create_pg_trgm_extension, noop),
        
        # Create search vector function
        migrations.RunPython(create_search_vector_function, drop_search_vector_function),
        
        # Create search vector trigger
        migrations.RunPython(create_search_vector_trigger, drop_search_vector_trigger),
        
        # Create search indexes
        migrations.RunPython(create_search_indexes, drop_search_indexes),
        
        # Update existing items
        migrations.RunPython(update_existing_search_vectors, noop),
    ]
