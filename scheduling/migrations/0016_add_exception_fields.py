# Generated manually for exception scheduling functionality

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0015_alter_schedulerequest_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='schedulerequest',
            name='is_exception',
            field=models.BooleanField(default=False, verbose_name='Agendamento de Exceção'),
        ),
        migrations.AddField(
            model_name='schedulerequest',
            name='exception_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Motivo da Exceção'),
        ),
        migrations.AddField(
            model_name='schedulerequest',
            name='created_by_technician',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'user_type': 'technician'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_exception_requests',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Criado pelo Técnico'
            ),
        ),
    ]