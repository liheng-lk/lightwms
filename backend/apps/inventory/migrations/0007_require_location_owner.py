from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_location_owner(apps, schema_editor):
    Location = apps.get_model('inventory', 'Location')
    User = apps.get_model('users', 'User')

    missing = Location.objects.filter(owner__isnull=True)
    if not missing.exists():
        return

    fallback = (
        User.objects.filter(role='super_admin', is_active=True).order_by('id').first()
        or User.objects.filter(role='item_manager', is_active=True).order_by('id').first()
        or User.objects.filter(is_active=True).order_by('id').first()
        or User.objects.order_by('id').first()
    )
    if fallback is None:
        raise RuntimeError(
            'Cannot make inventory_location.owner mandatory: existing locations have no owner and no user exists to backfill them.'
        )

    missing.update(owner_id=fallback.id)


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0006_add_location_owner'),
    ]

    operations = [
        migrations.RunPython(backfill_location_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='location',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='managed_locations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
