from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('laboratories', '0006_migrate_existing_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='laboratory',
            name='department',
        ),
    ]
