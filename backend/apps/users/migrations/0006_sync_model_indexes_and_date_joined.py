import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0005_oauth_state_and_identity_constraints'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='invitecode',
            new_name='users_invit_created_2fbdde_idx',
            old_name='users_invit_created_7e8c3a_idx',
        ),
        migrations.RenameIndex(
            model_name='invitecode',
            new_name='users_invit_is_acti_4d14ac_idx',
            old_name='users_invit_is_acti_d8f2e1_idx',
        ),
        migrations.RenameIndex(
            model_name='wechatoauthstate',
            new_name='users_wecha_expires_d2b2a6_idx',
            old_name='users_wecha_exp_oauth_idx',
        ),
        migrations.RenameIndex(
            model_name='wechatsession',
            new_name='users_wecha_expires_1f9a11_idx',
            old_name='users_wecha_expires_a1b2c3_idx',
        ),
        migrations.AlterField(
            model_name='user',
            name='date_joined',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined'),
        ),
    ]
