# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0010_draftschedulerequest_class_semester'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedulerequest',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Descrição da atividade'),
        ),
        migrations.AlterField(
            model_name='draftschedulerequest',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Descrição da atividade'),
        ),
    ]