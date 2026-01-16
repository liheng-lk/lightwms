"""
Migration for InviteCode and WechatSession models.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InviteCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('max_uses', models.PositiveIntegerField(default=1)),
                ('current_uses', models.PositiveIntegerField(default=0)),
                ('default_role', models.CharField(
                    choices=[
                        ('super_admin', 'Super Admin'),
                        ('item_manager', 'Item Manager'),
                        ('read_only_user', 'Read Only User')
                    ],
                    default='read_only_user',
                    max_length=20
                )),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_invite_codes',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'users_invitecode',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WechatSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(max_length=64, unique=True)),
                ('openid', models.CharField(max_length=100)),
                ('unionid', models.CharField(blank=True, max_length=100, null=True)),
                ('nickname', models.CharField(blank=True, default='', max_length=100)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'users_wechatsession',
            },
        ),
        # Add indexes for InviteCode
        migrations.AddIndex(
            model_name='invitecode',
            index=models.Index(fields=['-created_at'], name='users_invit_created_7e8c3a_idx'),
        ),
        migrations.AddIndex(
            model_name='invitecode',
            index=models.Index(fields=['is_active', '-created_at'], name='users_invit_is_acti_d8f2e1_idx'),
        ),
        # Add index for WechatSession
        migrations.AddIndex(
            model_name='wechatsession',
            index=models.Index(fields=['expires_at'], name='users_wecha_expires_a1b2c3_idx'),
        ),
    ]
