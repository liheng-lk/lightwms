from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_read_only_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('item_manager', 'Item Manager'),
                    ('read_only_user', '普通用户'),
                ],
                default='read_only_user',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='invitecode',
            name='default_role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('item_manager', 'Item Manager'),
                    ('read_only_user', '普通用户'),
                ],
                default='read_only_user',
                max_length=20,
            ),
        ),
    ]
