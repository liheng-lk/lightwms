from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0003_auditlog_immutable_trigger'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='target_id',
            field=models.PositiveBigIntegerField(),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='target_type',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('Item', 'Item'),
                    ('Category', 'Category'),
                    ('Location', 'Location'),
                    ('Warehouse', 'Warehouse'),
                    ('InviteCode', 'Invite Code'),
                    ('User', 'User'),
                    ('BorrowRecord', 'Borrow Record'),
                    ('TakeRecord', 'Take Record'),
                    ('ReplenishRecord', 'Replenish Record'),
                    ('ItemImage', 'Item Image'),
                    ('Invoice', 'Invoice'),
                    ('System', 'System Setting'),
                ],
            ),
        ),
    ]
