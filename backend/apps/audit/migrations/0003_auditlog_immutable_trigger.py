"""
Migration to create database-level immutability trigger for AuditLog.
This ensures AuditLog records cannot be updated or deleted even via raw SQL.

Note: These operations are PostgreSQL-specific and will be skipped on other databases.
"""
from django.db import migrations


def create_trigger_function(apps, schema_editor):
    """Create the trigger function if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION forbid_auditlog_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'AuditLog is immutable: UPDATE and DELETE operations are forbidden';
        END;
        $$ LANGUAGE plpgsql;
    """)


def drop_trigger_function(apps, schema_editor):
    """Drop the trigger function if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP FUNCTION IF EXISTS forbid_auditlog_modification();")


def create_update_trigger(apps, schema_editor):
    """Create the UPDATE trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE TRIGGER trg_auditlog_no_update
            BEFORE UPDATE ON audit_auditlog
            FOR EACH ROW
            EXECUTE FUNCTION forbid_auditlog_modification();
    """)


def drop_update_trigger(apps, schema_editor):
    """Drop the UPDATE trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS trg_auditlog_no_update ON audit_auditlog;")


def create_delete_trigger(apps, schema_editor):
    """Create the DELETE trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE TRIGGER trg_auditlog_no_delete
            BEFORE DELETE ON audit_auditlog
            FOR EACH ROW
            EXECUTE FUNCTION forbid_auditlog_modification();
    """)


def drop_delete_trigger(apps, schema_editor):
    """Drop the DELETE trigger if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS trg_auditlog_no_delete ON audit_auditlog;")


class Migration(migrations.Migration):
    """
    Creates a PostgreSQL trigger that prevents UPDATE and DELETE operations
    on the audit_auditlog table. This is the database-level protection layer
    for AuditLog immutability.
    """

    dependencies = [
        ('audit', '0002_add_auditlog'),
    ]

    operations = [
        # Create the trigger function
        migrations.RunPython(create_trigger_function, drop_trigger_function),
        # Create the trigger for UPDATE
        migrations.RunPython(create_update_trigger, drop_update_trigger),
        # Create the trigger for DELETE
        migrations.RunPython(create_delete_trigger, drop_delete_trigger),
    ]
