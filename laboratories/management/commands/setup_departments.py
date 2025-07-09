from django.core.management.base import BaseCommand
from laboratories.models import Department, Laboratory

class Command(BaseCommand):
    help = 'Cria departamentos e migra dados existentes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--migrate-data',
            action='store_true',
            help='Migrar dados dos laboratórios existentes',
        )
    
    def handle(self, *args, **options):
        # Criar departamentos
        self.create_departments()
        
        # Migrar dados se solicitado
        if options['migrate_data']:
            self.migrate_laboratory_data()
    
    def create_departments(self):
        departments_data = [
            {
                'code': 'exatas',
                'name': 'Ciências Exatas',
                'color': '#007bff',
                'description': 'Departamento de Ciências Exatas e Engenharia'
            },
            {
                'code': 'saude',
                'name': 'Ciências da Saúde',
                'color': '#dc3545',
                'description': 'Departamento de Ciências da Saúde e Biológicas'
            },
            {
                'code': 'informatica',
                'name': 'Informática',
                'color': '#28a745',
                'description': 'Departamento de Informática e Computação'
            }
        ]
        
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Departamento "{dept.name}" criado')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Departamento "{dept.name}" já existe')
                )
    
    def migrate_laboratory_data(self):
        """Migra dados do campo antigo para o novo"""
        self.stdout.write('🔄 Migrando dados dos laboratórios...')
        
        # Criar dicionário de departamentos
        departments = {
            'exatas': Department.objects.get(code='exatas'),
            'saude': Department.objects.get(code='saude'),
            'informatica': Department.objects.get(code='informatica'),
        }
        
        migrated_count = 0
        
        for lab in Laboratory.objects.all():
            # Se já tem departamentos novos, pular
            if lab.departments.exists():
                continue
            
            # Migrar do campo antigo
            if lab.department and lab.department in departments:
                lab.departments.add(departments[lab.department])
                migrated_count += 1
                self.stdout.write(f'  ✅ {lab.name} -> {departments[lab.department].name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {migrated_count} laboratórios migrados')
        )
