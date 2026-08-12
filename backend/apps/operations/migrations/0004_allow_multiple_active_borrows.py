"""Allow multiple active borrow records for multi-quantity reusable items.

The original schema enforced one active borrow per item. That invariant became
invalid when reusable Item.quantity was introduced: a quantity-3 item must be
able to have three independent active borrow records at the same time.
"""
from django.db import migrations


def drop_single_active_borrow_index(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('DROP INDEX IF EXISTS uq_borrow_active_item;')


def restore_single_active_borrow_index(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("""
            CREATE UNIQUE INDEX uq_borrow_active_item
            ON operations_borrowrecord (item_id)
            WHERE status = 'active';
        """)


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0003_add_quantity_to_borrow_record'),
    ]

    operations = [
        migrations.RunPython(
            drop_single_active_borrow_index,
            restore_single_active_borrow_index,
        ),
    ]
