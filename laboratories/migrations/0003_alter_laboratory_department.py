# Generated by Django 5.2 on 2025-04-23 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0002_alter_laboratory_options_laboratory_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laboratory',
            name='department',
            field=models.CharField(choices=[('exatas', 'Exatas'), ('saude', 'Saúde'), ('informatica', 'Informática')], max_length=100, verbose_name='Departamento'),
        ),
    ]
