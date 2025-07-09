from django.db import migrations

def migrate_departments(apps, schema_editor):
    """Migrar departamentos existentes para nova estrutura"""
    Department = apps.get_model('laboratories', 'Department')
    Laboratory = apps.get_model('laboratories', 'Laboratory')
    
    # Criar departamentos padrão
    departments_data = [
        {'code': 'exatas', 'name': 'Exatas', 'color': '#007bff'},
        {'code': 'saude', 'name': 'Saúde', 'color': '#dc3545'},
        {'code': 'informatica', 'name': 'Informática', 'color': '#28a745'},
    ]
    
    departments = {}
    for dept_data in departments_data:
        dept, created = Department.objects.get_or_create(
            code=dept_data['code'],
            defaults={
                'name': dept_data['name'],
                'color': dept_data['color']
            }
        )
        departments[dept_data['code']] = dept
    
    # Migrar laboratórios existentes
    for lab in Laboratory.objects.all():
        if hasattr(lab, 'department') and lab.department:
            # Mapear departamento antigo para novo
            old_dept = lab.department.lower()
            if old_dept in departments:
                lab.departments.add(departments[old_dept])

def reverse_migrate_departments(apps, schema_editor):
    """Reverter migração se necessário"""
    Department = apps.get_model('laboratories', 'Department')
    Department.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('laboratories', '0005_add_departments'),
    ]

    operations = [
        migrations.RunPython(
            migrate_departments, 
            reverse_migrate_departments
        ),
    ]