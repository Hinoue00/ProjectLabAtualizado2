from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('laboratories', '0004_fix_department_values'),
    ]

    operations = [
        # Criar modelo Department
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Código')),
                ('name', models.CharField(max_length=100, verbose_name='Nome')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descrição')),
                ('color', models.CharField(default='#007bff', help_text='Cor em hexadecimal (ex: #007bff)', max_length=7, verbose_name='Cor')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
                'ordering': ['name'],
            },
        ),
        
        # Adicionar campo ManyToMany
        migrations.AddField(
            model_name='laboratory',
            name='departments',
            field=models.ManyToManyField(
                help_text='Selecione os departamentos aos quais este laboratório pertence',
                to='laboratories.Department',
                verbose_name='Departamentos'
            ),
        ),
    ]