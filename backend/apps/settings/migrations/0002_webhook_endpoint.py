# Migration for WebhookEndpoint model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('settings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookEndpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=2048)),
                ('secret', models.CharField(blank=True, default='', max_length=255)),
                ('events', models.JSONField(default=list, help_text='List of event type strings, e.g. ["item_created", "borrow_created"]')),
                ('is_active', models.BooleanField(default=True)),
                ('name', models.CharField(blank=True, default='', max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='webhook_endpoints',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'settings_webhook_endpoint',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['is_active', '-created_at'], name='settings_webhook_active_idx'),
                ],
            },
        ),
    ]
