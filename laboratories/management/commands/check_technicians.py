from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Verifica se existem técnicos aprovados no sistema'
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 VERIFICANDO TÉCNICOS NO SISTEMA')
        self.stdout.write('=' * 50)
        
        # Verificar todos os técnicos
        all_technicians = User.objects.filter(user_type='technician')
        self.stdout.write(f'👥 TOTAL DE TÉCNICOS: {all_technicians.count()}')
        
        for tech in all_technicians:
            status = []
            if tech.is_active:
                status.append('✅ Ativo')
            else:
                status.append('❌ Inativo')
                
            if tech.is_approved:
                status.append('✅ Aprovado')
            else:
                status.append('❌ Não aprovado')
            
            self.stdout.write(f'   - {tech.get_full_name()} ({tech.email})')
            self.stdout.write(f'     Status: {" | ".join(status)}')
        
        # Verificar técnicos que aparecerão no formulário
        form_technicians = User.objects.filter(
            user_type='technician', 
            is_approved=True, 
            is_active=True
        )
        
        self.stdout.write(f'\n🎯 TÉCNICOS DISPONÍVEIS NO FORMULÁRIO: {form_technicians.count()}')
        
        if form_technicians.exists():
            for tech in form_technicians:
                self.stdout.write(f'   ✅ {tech.get_full_name()} ({tech.email})')
        else:
            self.stdout.write('   ⚠️ NENHUM técnico disponível para o formulário!')
            self.stdout.write('   💡 Para resolver:')
            self.stdout.write('      1. Certifique-se que existe pelo menos um usuário com user_type="technician"')
            self.stdout.write('      2. Certifique-se que este usuário tem is_approved=True')
            self.stdout.write('      3. Certifique-se que este usuário tem is_active=True')
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('✅ VERIFICAÇÃO CONCLUÍDA')