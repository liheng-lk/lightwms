"""
Migration for creating TakeRecord and ReplenishRecord models.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('operations', '0001_create_borrowrecord'),
        ('inventory', '0004_item_search_indexes'),
    ]

    operations = [
        # Create TakeRecord model
        migrations.CreateModel(
            name='TakeRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='take_records', to='inventory.item')),
                ('taker', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='taken_records', to=settings.AUTH_USER_MODEL)),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='operated_take_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'operations_takerecord',
                'ordering': ['-created_at'],
            },
        ),
        # Create ReplenishRecord model
        migrations.CreateModel(
            name='ReplenishRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='replenish_records', to='inventory.item')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='operated_replenish_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'operations_replenishrecord',
                'ordering': ['-created_at'],
            },
        ),
        # Create indexes for TakeRecord
        migrations.AddIndex(
            model_name='takerecord',
            index=models.Index(fields=['item', '-created_at'], name='operations__item_ta_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='takerecord',
            index=models.Index(fields=['taker', '-created_at'], name='operations__taker_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='takerecord',
            index=models.Index(fields=['operator', '-created_at'], name='operations__op_take_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='takerecord',
            index=models.Index(fields=['-created_at'], name='operations__take_cr_j0k1l2_idx'),
        ),
        # Create indexes for ReplenishRecord
        migrations.AddIndex(
            model_name='replenishrecord',
            index=models.Index(fields=['item', '-created_at'], name='operations__item_re_m3n4o5_idx'),
        ),
        migrations.AddIndex(
            model_name='replenishrecord',
            index=models.Index(fields=['operator', '-created_at'], name='operations__op_rep_p6q7r8_idx'),
        ),
        migrations.AddIndex(
            model_name='replenishrecord',
            index=models.Index(fields=['-created_at'], name='operations__rep_cr_s9t0u1_idx'),
        ),
    ]
