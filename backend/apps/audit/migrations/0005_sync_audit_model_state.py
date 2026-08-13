from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0004_system_target_and_bigint_target_id'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='loginlog',
            name='audit_login_ip_5b6185_idx',
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('create', 'Create'),
                    ('update', 'Update'),
                    ('delete', 'Delete'),
                    ('deactivate', 'Deactivate'),
                    ('borrow', 'Borrow'),
                    ('return', 'Return'),
                    ('take', 'Take'),
                    ('replenish', 'Replenish'),
                    ('invite_use', 'Invite Use'),
                    ('login', 'Login'),
                    ('logout', 'Logout'),
                    ('import', 'Import'),
                    ('export', 'Export'),
                ],
                max_length=20,
            ),
        ),
    ]
