from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('laboratories', '0009_laboratory_department_alter_laboratory_capacity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='laboratory',
            name='department',
            field=models.CharField(
                blank=True, 
                null=True, 
                choices=[
                    ('exatas', 'Exatas'), 
                    ('saude', 'Saúde'), 
                    ('informatica', 'Informática')
                ], 
                help_text='Este campo será substituído em breve', 
                max_length=100, 
                verbose_name='Departamento (Antigo)'
            ),
        ),
    ]