from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),  # Ajuste conforme suas migrations
        ('laboratories', '0007_remove_old_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='laboratory',
            name='responsible_technicians',
            field=models.ManyToManyField(
                blank=True,
                help_text='Selecione os técnicos responsáveis por este laboratório',
                limit_choices_to={'user_type': 'technician', 'is_approved': True},
                related_name='managed_laboratories',
                to='accounts.User',
                verbose_name='Técnicos Responsáveis'
            ),
        ),
    ]