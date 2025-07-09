from django.core.management.base import BaseCommand
from laboratories.models import Laboratory, Department
from accounts.models import User

class Command(BaseCommand):
    help = 'Testa sistema de múltiplos técnicos responsáveis'
    
    def handle(self, *args, **options):
        self.stdout.write('🧪 TESTANDO MÚLTIPLOS TÉCNICOS')
        self.stdout.write('=' * 50)
        
        # Listar técnicos disponíveis
        technicians = User.objects.filter(
            user_type='technician', 
            is_approved=True, 
            is_active=True
        )
        
        self.stdout.write(f'👨‍🔧 TÉCNICOS DISPONÍVEIS: {technicians.count()}')
        for tech in technicians:
            self.stdout.write(f'   - {tech.get_full_name()} ({tech.email})')
        
        # Testar criação de laboratório com múltiplos técnicos
        if technicians.count() >= 2:
            exatas = Department.objects.get(code='exatas')
            
            lab = Laboratory.objects.create(
                name='Lab Teste - Múltiplos Técnicos',
                location='Bloco T - Sala 999',
                capacity=20,
                is_active=True
            )
            
            # Adicionar departamento
            lab.departments.add(exatas)
            
            # Adicionar múltiplos técnicos
            lab.responsible_technicians.add(*technicians[:2])
            
            self.stdout.write(f'\n✅ LABORATÓRIO CRIADO:')
            self.stdout.write(f'   Nome: {lab.name}')
            self.stdout.write(f'   Departamentos: {lab.get_departments_display()}')
            self.stdout.write(f'   Técnicos: {lab.get_technicians_display()}')
            
            # Testar métodos
            first_tech = technicians.first()
            self.stdout.write(f'\n🔍 TESTES:')
            self.stdout.write(f'   {first_tech.get_full_name()} é responsável: {lab.has_technician(first_tech)}')
            self.stdout.write(f'   Total de técnicos: {len(lab.get_technicians_list())}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ TESTE CONCLUÍDO'))