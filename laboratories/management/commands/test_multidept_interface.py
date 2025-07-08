from django.core.management.base import BaseCommand
from laboratories.models import Laboratory, Department

class Command(BaseCommand):
    help = 'Testa criação de laboratório multidisciplinar via código'
    
    def handle(self, *args, **options):
        self.stdout.write('🧪 TESTANDO CRIAÇÃO DE LABORATÓRIO MULTIDISCIPLINAR')
        
        # Buscar departamentos
        exatas = Department.objects.get(code='exatas')
        saude = Department.objects.get(code='saude')
        
        # Criar laboratório multidisciplinar
        lab = Laboratory.objects.create(
            name='Laboratório Multidisciplinar - Teste',
            location='Bloco B - Sala 200',
            capacity=25,
            description='Laboratório para atividades interdisciplinares',
            is_active=True
        )
        
        # Adicionar múltiplos departamentos
        lab.departments.add(exatas, saude)
        
        self.stdout.write(f'✅ Laboratório criado: {lab.name}')
        self.stdout.write(f'   Departamentos: {lab.get_departments_display()}')
        self.stdout.write(f'   Pertence a Exatas: {lab.belongs_to_department("exatas")}')
        self.stdout.write(f'   Pertence a Saúde: {lab.belongs_to_department("saude")}')
        self.stdout.write(f'   Pertence a Informática: {lab.belongs_to_department("informatica")}')