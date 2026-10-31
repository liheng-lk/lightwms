from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invoices', '0002_add_project_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailboxAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, default='', max_length=80)),
                ('email', models.EmailField(max_length=254)),
                ('provider', models.CharField(choices=[('qq', 'QQ 邮箱'), ('163', '网易 163'), ('126', '网易 126'), ('gmail', 'Gmail'), ('outlook', 'Outlook / Microsoft 365'), ('custom', '其他 IMAP')], max_length=20)),
                ('imap_host', models.CharField(max_length=255)),
                ('imap_port', models.PositiveIntegerField(default=993)),
                ('secret_encrypted', models.TextField()),
                ('last_error', models.CharField(blank=True, default='', max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mailbox_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'invoices_mailbox_account',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='mailboxaccount',
            constraint=models.UniqueConstraint(fields=('user', 'email'), name='uq_mailbox_user_email'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='mailbox',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='invoices.mailboxaccount'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='source_key',
            field=models.CharField(blank=True, max_length=220, null=True, unique=True),
        ),
    ]
