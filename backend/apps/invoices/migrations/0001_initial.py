"""
Initial migration for invoices app.
Creates the Invoice model.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0004_item_search_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('category', models.CharField(max_length=100)),
                ('custom_type', models.CharField(blank=True, default='', max_length=100)),
                ('file', models.CharField(max_length=500)),
                ('original_filename', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', '未报销'), ('reimbursed', '已报销'), ('rejected', '无法报销')], default='pending', max_length=20)),
                ('registered_month', models.CharField(max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_invoices', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='inventory.item')),
            ],
            options={
                'db_table': 'invoices_invoice',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['-created_at'], name='invoices_in_created_7e3c8e_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['registered_month', '-created_at'], name='invoices_in_registe_c8e5a5_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['status', '-created_at'], name='invoices_in_status_e8f3a2_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['category', '-created_at'], name='invoices_in_categor_d5f2b1_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['item', '-created_at'], name='invoices_in_item_id_a3e4c9_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['created_by', '-created_at'], name='invoices_in_created_b2d1e8_idx'),
        ),
    ]
