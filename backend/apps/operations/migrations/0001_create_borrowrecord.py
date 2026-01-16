"""
Migration for creating BorrowRecord model with partial unique index.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_borrow_active_index(apps, schema_editor):
    """Create partial unique index for active borrows if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE UNIQUE INDEX uq_borrow_active_item 
        ON operations_borrowrecord (item_id) 
        WHERE status = 'active';
    """)


def drop_borrow_active_index(apps, schema_editor):
    """Drop partial unique index for active borrows if on PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS uq_borrow_active_item;")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0004_item_search_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='BorrowRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expected_return_date', models.DateField()),
                ('actual_return_datetime', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('return_notes', models.TextField(blank=True, default='')),
                ('condition', models.CharField(blank=True, default='', max_length=200)),
                ('status', models.CharField(choices=[('active', 'Active'), ('returned', 'Returned')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('borrower', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='borrowed_records', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='borrow_records', to='inventory.item')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='operated_borrow_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'operations_borrowrecord',
                'ordering': ['-created_at'],
            },
        ),
        # Create indexes
        migrations.AddIndex(
            model_name='borrowrecord',
            index=models.Index(fields=['item', 'status'], name='operations__item_id_e8e8e5_idx'),
        ),
        migrations.AddIndex(
            model_name='borrowrecord',
            index=models.Index(fields=['borrower', '-created_at'], name='operations__borrowe_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='borrowrecord',
            index=models.Index(fields=['operator', '-created_at'], name='operations__operato_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='borrowrecord',
            index=models.Index(fields=['-created_at'], name='operations__created_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='borrowrecord',
            index=models.Index(fields=['expected_return_date'], name='operations__expecte_j0k1l2_idx'),
        ),
        # Create partial unique index: only one active borrow per item
        # This is PostgreSQL-specific and will be skipped on other databases
        migrations.RunPython(create_borrow_active_index, drop_borrow_active_index),
    ]
