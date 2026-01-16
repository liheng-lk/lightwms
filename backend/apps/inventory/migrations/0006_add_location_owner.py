# Generated migration for adding owner field to Location model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0005_update_quantity_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='managed_locations',
                to=settings.AUTH_USER_MODEL,
                # 临时允许 null，后续需要填充数据后再改为必填
                null=True,
            ),
        ),
    ]
