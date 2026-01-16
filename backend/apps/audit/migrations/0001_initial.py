"""
Initial migration for audit app.
Creates LoginLog model.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username_attempted', models.CharField(max_length=150)),
                ('success', models.BooleanField()),
                ('ip', models.GenericIPAddressField()),
                ('user_agent', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='login_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'audit_loginlog',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='loginlog',
            index=models.Index(fields=['user', '-created_at'], name='audit_login_user_id_7e8c3a_idx'),
        ),
        migrations.AddIndex(
            model_name='loginlog',
            index=models.Index(fields=['ip', '-created_at'], name='audit_login_ip_3f2a1b_idx'),
        ),
        migrations.AddIndex(
            model_name='loginlog',
            index=models.Index(fields=['-created_at'], name='audit_login_created_4d5e6f_idx'),
        ),
    ]
