from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from accounts.models import User
from dashboard.views import technician_dashboard, professor_dashboard
import json

class Command(BaseCommand):
    help = 'Testa requisições AJAX do calendário'
    
    def handle(self, *args, **options):
        self.stdout.write('🧪 TESTANDO REQUISIÇÕES AJAX DO CALENDÁRIO')
        self.stdout.write('=' * 60)
        
        # Setup
        factory = RequestFactory()
        
        # ==========================================
        # 1. TESTAR DASHBOARD TÉCNICO
        # ==========================================
        
        self.stdout.write('\n🔧 TESTANDO DASHBOARD TÉCNICO:')
        self.stdout.write('-' * 35)
        
        # Buscar um técnico
        technician = User.objects.filter(user_type='technician', is_active=True).first()
        
        if technician:
            self.stdout.write(f'👨‍🔧 Técnico de teste: {technician.get_full_name()}')
            
            # Teste 1: Requisição normal (não-AJAX)
            self.stdout.write('\n📄 Teste 1: Requisição normal (não-AJAX)')
            request = factory.get('/dashboard/technician/?week_offset=0&department=all')
            request.user = technician
            
            try:
                response = technician_dashboard(request)
                self.stdout.write(f'   ✅ Status: {response.status_code}')
                self.stdout.write(f'   ✅ Tipo: {type(response).__name__}')
                
                if hasattr(response, 'content'):
                    content_length = len(response.content)
                    self.stdout.write(f'   ✅ Conteúdo: {content_length} bytes')
                    
            except Exception as e:
                self.stdout.write(f'   ❌ Erro: {e}')
            
            # Teste 2: Requisição AJAX
            self.stdout.write('\n📡 Teste 2: Requisição AJAX')
            request = factory.get(
                '/dashboard/technician/?week_offset=1&department=exatas',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            request.user = technician
            
            try:
                response = technician_dashboard(request)
                self.stdout.write(f'   ✅ Status: {response.status_code}')
                self.stdout.write(f'   ✅ Tipo: {type(response).__name__}')
                
                if hasattr(response, 'content'):
                    try:
                        data = json.loads(response.content.decode('utf-8'))
                        self.stdout.write(f'   ✅ JSON válido: {data.get("success", False)}')
                        
                        if 'html' in data:
                            html_length = len(data['html'])
                            self.stdout.write(f'   ✅ HTML length: {html_length} chars')
                        
                        if 'error' in data:
                            self.stdout.write(f'   ⚠️ Erro retornado: {data["error"]}')
                            
                    except json.JSONDecodeError as e:
                        self.stdout.write(f'   ❌ JSON inválido: {e}')
                        self.stdout.write(f'   📄 Conteúdo: {response.content[:200]}...')
                        
            except Exception as e:
                self.stdout.write(f'   ❌ Erro: {e}')
                import traceback
                self.stdout.write(f'   📄 Traceback: {traceback.format_exc()[:500]}...')
        else:
            self.stdout.write('⚠️ Nenhum técnico encontrado para teste')
        
        # ==========================================
        # 2. TESTAR DASHBOARD PROFESSOR
        # ==========================================
        
        self.stdout.write('\n👨‍🏫 TESTANDO DASHBOARD PROFESSOR:')
        self.stdout.write('-' * 37)
        
        # Buscar um professor
        professor = User.objects.filter(user_type='professor', is_active=True).first()
        
        if professor:
            self.stdout.write(f'👨‍🏫 Professor de teste: {professor.get_full_name()}')
            
            # Teste AJAX
            self.stdout.write('\n📡 Teste: Requisição AJAX')
            request = factory.get(
                '/dashboard/professor/?week_offset=0&department=all',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            request.user = professor
            
            try:
                response = professor_dashboard(request)
                self.stdout.write(f'   ✅ Status: {response.status_code}')
                
                if hasattr(response, 'content'):
                    try:
                        data = json.loads(response.content.decode('utf-8'))
                        self.stdout.write(f'   ✅ JSON válido: {data.get("success", False)}')
                        
                        if 'html' in data:
                            html_length = len(data['html'])
                            self.stdout.write(f'   ✅ HTML length: {html_length} chars')
                            
                    except json.JSONDecodeError as e:
                        self.stdout.write(f'   ❌ JSON inválido: {e}')
                        
            except Exception as e:
                self.stdout.write(f'   ❌ Erro: {e}')
        else:
            self.stdout.write('⚠️ Nenhum professor encontrado para teste')
        
        # ==========================================
        # 3. TESTAR TEMPLATES PARCIAIS
        # ==========================================
        
        self.stdout.write('\n📄 TESTANDO TEMPLATES PARCIAIS:')
        self.stdout.write('-' * 32)
        
        from django.template.loader import get_template
        
        # Testar template do técnico
        try:
            template = get_template('partials/calendar_week_technician.html')
            self.stdout.write('   ✅ Template técnico encontrado')
        except Exception as e:
            self.stdout.write(f'   ❌ Template técnico não encontrado: {e}')
        
        # Testar template do professor
        try:
            template = get_template('partials/calendar_week_professor.html')
            self.stdout.write('   ✅ Template professor encontrado')
        except Exception as e:
            self.stdout.write(f'   ❌ Template professor não encontrado: {e}')
        
        # ==========================================
        # 4. VERIFICAR LOGS
        # ==========================================
        
        self.stdout.write('\n📋 DICAS PARA DEBUG:')
        self.stdout.write('-' * 20)
        self.stdout.write('1. Verifique o console do navegador (F12)')
        self.stdout.write('2. Monitore a aba Network para ver requisições AJAX')
        self.stdout.write('3. Verifique se há erros 500 nas requisições')
        self.stdout.write('4. Verifique se os templates parciais existem')
        self.stdout.write('5. Execute: tail -f logs/django.log (se logs existirem)')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ TESTE AJAX CONCLUÍDO'))
        
        # ==========================================
        # 5. SIMULAR PROBLEMA REAL
        # ==========================================
        
        self.stdout.write('\n🔍 SIMULANDO PROBLEMA REAL:')
        self.stdout.write('-' * 28)
        
        self.stdout.write('Para resolver carregamento infinito:')
        self.stdout.write('1. Substitua dashboard/views.py pelo código corrigido')
        self.stdout.write('2. Verifique se templates parciais existem')
        self.stdout.write('3. Reinicie o servidor Django')
        self.stdout.write('4. Limpe cache do navegador (Ctrl+F5)')
        self.stdout.write('5. Teste novamente')