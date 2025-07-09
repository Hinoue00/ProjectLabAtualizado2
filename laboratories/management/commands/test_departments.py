from django.core.management.base import BaseCommand
from laboratories.models import Laboratory, Department

class Command(BaseCommand):
    help = 'Testa sistema de múltiplos departamentos'
    
    def handle(self, *args, **options):
        self.stdout.write('🧪 TESTANDO SISTEMA DE DEPARTAMENTOS')
        self.stdout.write('=' * 50)
        
        # Verificar se departamentos existem
        dept_count = Department.objects.count()
        self.stdout.write(f'📊 Departamentos cadastrados: {dept_count}')
        
        if dept_count == 0:
            self.stdout.write(self.style.WARNING('⚠️ Execute: python manage.py setup_departments'))
            return
        
        # Listar laboratórios e seus departamentos
        self.stdout.write('\n🏢 LABORATÓRIOS E DEPARTAMENTOS:')
        
        for lab in Laboratory.objects.all():
            old_dept = lab.department if hasattr(lab, 'department') else 'N/A'
            new_depts = lab.get_departments_display()
            
            self.stdout.write(f'  📋 {lab.name}:')
            self.stdout.write(f'     Antigo: {old_dept}')
            self.stdout.write(f'     Novo: {new_depts}')
            
            # Testar método de verificação
            for dept in Department.objects.all():
                belongs = lab.belongs_to_department(dept.code)
                icon = '✅' if belongs else '❌'
                self.stdout.write(f'     {icon} {dept.name}: {belongs}')
        
        # Testar filtros
        self.stdout.write('\n🔍 TESTANDO FILTROS:')
        
        from dashboard.views import get_laboratories_by_department
        
        for dept in Department.objects.all():
            filtered = get_laboratories_by_department(dept.code)
            self.stdout.write(f'  🏷️ {dept.name}: {filtered.count()} laboratórios')
            
            for lab in filtered:
                self.stdout.write(f'     - {lab.name}')
        
        all_labs = get_laboratories_by_department('all')
        self.stdout.write(f'  🏷️ Todos: {all_labs.count()} laboratórios')
        
        self.stdout.write(self.style.SUCCESS('\n✅ TESTE CONCLUÍDO'))