from django.core.management.base import BaseCommand
from laboratories.models import Laboratory

class Command(BaseCommand):
    help = 'Migra técnicos do campo antigo para o novo sistema'
    
    def handle(self, *args, **options):
        self.stdout.write('🔄 MIGRANDO TÉCNICOS RESPONSÁVEIS')
        self.stdout.write('=' * 50)
        
        migrated_count = 0
        
        for lab in Laboratory.objects.all():
            # Se já tem técnicos no novo sistema, pular
            if lab.responsible_technicians.exists():
                self.stdout.write(f'⏭️ {lab.name}: já tem técnicos no novo sistema')
                continue
            
            # Se tem técnico no campo antigo, migrar
            if lab.responsible_technician:
                lab.responsible_technicians.add(lab.responsible_technician)
                migrated_count += 1
                self.stdout.write(f'✅ {lab.name}: {lab.responsible_technician.get_full_name()} migrado')
            else:
                self.stdout.write(f'⚠️ {lab.name}: sem técnico responsável')
        
        self.stdout.write(f'\n📊 RESUMO:')
        self.stdout.write(f'   Laboratórios migrados: {migrated_count}')
        self.stdout.write(f'   Total de laboratórios: {Laboratory.objects.count()}')
        self.stdout.write(self.style.SUCCESS('✅ MIGRAÇÃO CONCLUÍDA'))