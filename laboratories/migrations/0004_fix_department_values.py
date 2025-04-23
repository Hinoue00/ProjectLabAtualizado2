from django.db import migrations

def fix_departments(apps, schema_editor):
    Laboratory = apps.get_model('laboratories', 'Laboratory')
    
    # Atualizar todos os laboratórios com um valor padrão sensato
    for lab in Laboratory.objects.all():
        # Verificar se o department é um timestamp
        if isinstance(lab.department, str) and any(c.isdigit() for c in lab.department):
            # Definir um valor padrão
            lab.department = 'exatas'  # ou use lógica para determinar o departamento correto
            lab.save()

class Migration(migrations.Migration):
    dependencies = [
        # Ajuste para a sua última migração
        ('laboratories', '0003_alter_laboratory_department'),
    ]

    operations = [
        migrations.RunPython(fix_departments),
    ]