"""
Migration for creating Item and ItemImage models.

Creates:
- Item model with all fields and constraints
- ItemImage model with partial unique constraint for primary image
- Partial unique index on barcode (uq_item_barcode_not_null)

Note: Some constraints are PostgreSQL-specific and will be skipped on other databases.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.search


def create_barcode_partial_unique(apps, schema_editor):
    """Create partial unique index on barcode for PostgreSQL."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE UNIQUE INDEX uq_item_barcode_not_null 
        ON inventory_item (barcode) 
        WHERE barcode IS NOT NULL;
    """)


def drop_barcode_partial_unique(apps, schema_editor):
    """Drop partial unique index on barcode."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS uq_item_barcode_not_null;")


def create_itemimage_primary_unique(apps, schema_editor):
    """Create partial unique index for primary image."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE UNIQUE INDEX uq_itemimage_primary 
        ON inventory_itemimage (item_id) 
        WHERE is_primary = true;
    """)


def drop_itemimage_primary_unique(apps, schema_editor):
    """Drop partial unique index for primary image."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS uq_itemimage_primary;")


def noop(apps, schema_editor):
    """No-op function."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0002_create_category'),
    ]

    operations = [
        # Create Item model
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('sku', models.CharField(max_length=50, unique=True)),
                ('barcode', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(blank=True, default='', max_length=20)),
                ('description', models.TextField(blank=True, default='')),
                ('type', models.CharField(choices=[('reusable', 'Reusable'), ('consumable', 'Consumable')], default='reusable', max_length=20)),
                ('status', models.CharField(choices=[('available', 'Available'), ('borrowed', 'Borrowed'), ('in_stock', 'In Stock'), ('out_of_stock', 'Out of Stock')], default='available', max_length=20)),
                ('quantity', models.PositiveIntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='items', to='inventory.category')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='items', to='inventory.location')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='owned_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'inventory_item',
                'ordering': ['-updated_at', '-id'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['is_active', '-updated_at', '-id'], name='inventory_i_is_acti_7e8c3a_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['owner', 'is_active'], name='inventory_i_owner_i_8f9d2b_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['location', 'is_active'], name='inventory_i_locatio_3c4e5f_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['category', 'is_active'], name='inventory_i_categor_6a7b8c_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['type', 'status'], name='inventory_i_type_st_9d0e1f_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['sku'], name='inventory_i_sku_2a3b4c_idx'),
        ),
        # Add unique constraint on SKU (named)
        migrations.AddConstraint(
            model_name='item',
            constraint=models.UniqueConstraint(fields=['sku'], name='uq_item_sku'),
        ),
        # Create partial unique index on barcode (PostgreSQL only)
        migrations.RunPython(create_barcode_partial_unique, drop_barcode_partial_unique),
        
        # Create ItemImage model
        migrations.CreateModel(
            name='ItemImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original', models.CharField(max_length=500)),
                ('thumb_256', models.CharField(max_length=500)),
                ('thumb_768', models.CharField(max_length=500)),
                ('thumb_1600', models.CharField(max_length=500)),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='inventory.item')),
            ],
            options={
                'db_table': 'inventory_itemimage',
                'ordering': ['-created_at'],
            },
        ),
        # Add indexes for ItemImage
        migrations.AddIndex(
            model_name='itemimage',
            index=models.Index(fields=['item', 'is_primary'], name='inventory_i_item_id_5e6f7g_idx'),
        ),
        migrations.AddIndex(
            model_name='itemimage',
            index=models.Index(fields=['item', '-created_at'], name='inventory_i_item_cr_8h9i0j_idx'),
        ),
        # Create partial unique index for primary image (PostgreSQL only)
        migrations.RunPython(create_itemimage_primary_unique, drop_itemimage_primary_unique),
    ]
