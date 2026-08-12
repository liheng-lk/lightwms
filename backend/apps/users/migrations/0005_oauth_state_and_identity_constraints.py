from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_restore_read_only_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='WechatOAuthState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=100, unique=True)),
                ('redirect_uri', models.CharField(blank=True, default='', max_length=500)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'users_wechatoauthstate'},
        ),
        migrations.AddIndex(
            model_name='wechatoauthstate',
            index=models.Index(fields=['expires_at'], name='users_wecha_exp_oauth_idx'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=('wechat_openid',),
                condition=Q(wechat_openid__isnull=False),
                name='uq_user_wechat_openid_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='invitecode',
            constraint=models.CheckConstraint(
                condition=Q(current_uses__lte=F('max_uses')),
                name='ck_invite_current_uses_lte_max_uses',
            ),
        ),
    ]
