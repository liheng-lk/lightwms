# Generated migration to remove read_only_user role

from django.db import migrations, models


def migrate_read_only_users(apps, schema_editor):
    """
    Migrate all read_only_user accounts to item_manager role.
    """
    User = apps.get_model('users', 'User')
    User.objects.filter(role='read_only_user').update(role='item_manager')
    
    # Also update invite codes with read_only_user default role
    InviteCode = apps.get_model('users', 'InviteCode')
    InviteCode.objects.filter(default_role='read_only_user').update(default_role='item_manager')


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - no action needed as we can't know which users were originally read_only_user.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_invitecode_wechatsession'),
    ]

    operations = [
        migrations.RunPython(migrate_read_only_users, reverse_migration),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('super_admin', 'Super Admin'), ('item_manager', 'Item Manager')],
                default='item_manager',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='invitecode',
            name='default_role',
            field=models.CharField(
                choices=[('super_admin', 'Super Admin'), ('item_manager', 'Item Manager')],
                default='item_manager',
                max_length=20,
            ),
        ),
    ]
