from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0009_laboratory_department_alter_laboratory_capacity_and_more'),
    ]

    operations = [
        # Primeiro, remover a restrição NOT NULL se ela ainda existir
        migrations.RunSQL(
            sql="ALTER TABLE laboratories_laboratory ALTER COLUMN department DROP NOT NULL;",
            reverse_sql="ALTER TABLE laboratories_laboratory ALTER COLUMN department SET NOT NULL;",
        ),
        
        # Depois, garantir que o campo está corretamente definido no Django
        migrations.AlterField(
            model_name='laboratory',
            name='department',
            field=models.CharField(
                blank=True, 
                choices=[('exatas', 'Exatas'), ('saude', 'Saúde'), ('informatica', 'Informática')], 
                help_text='Este campo será substituído em breve', 
                max_length=100, 
                null=True, 
                verbose_name='Departamento (Antigo)'
            ),
        ),
    ]