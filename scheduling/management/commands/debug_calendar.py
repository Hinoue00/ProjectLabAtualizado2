from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from scheduling.models import ScheduleRequest, Laboratory
from accounts.models import User

class Command(BaseCommand):
    help = 'Debug específico do calendário semanal'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--professor-id',
            type=int,
            default=None,
            help='ID do professor para testar (padrão: primeiro professor encontrado)',
        )
        parser.add_argument(
            '--week-offset',
            type=int,
            default=0,
            help='Offset da semana (0=esta semana, -1=semana passada, 1=próxima semana)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 DEBUG ESPECÍFICO DO CALENDÁRIO SEMANAL'))
        self.stdout.write('=' * 60)
        
        # ==========================================
        # DEFINIR PROFESSOR PARA TESTE
        # ==========================================
        if options['professor_id']:
            try:
                professor = User.objects.get(id=options['professor_id'], user_type='professor')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Professor ID {options["professor_id"]} não encontrado'))
                return
        else:
            # Pegar o primeiro professor ativo
            professor = User.objects.filter(user_type='professor', is_approved=True).first()
            if not professor:
                self.stdout.write(self.style.ERROR('❌ Nenhum professor ativo encontrado'))
                return
        
        self.stdout.write(f"🧑‍🏫 TESTANDO COM PROFESSOR: {professor.get_full_name()} (ID: {professor.id})")
        
        # ==========================================
        # CALCULAR SEMANA PARA TESTE
        # ==========================================
        today = timezone.now().date()
        week_offset = options['week_offset']
        
        # Cálculo da semana (segunda a sexta)
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=4)  # Segunda a sexta
        
        self.stdout.write(f"📅 PERÍODO TESTADO: {start_of_week} até {end_of_week}")
        self.stdout.write(f"📅 OFFSET DA SEMANA: {week_offset}")
        
        # ==========================================
        # BUSCAR TODOS OS AGENDAMENTOS DO PROFESSOR
        # ==========================================
        all_schedules = ScheduleRequest.objects.filter(professor=professor)
        self.stdout.write(f"\n📊 TOTAL DE AGENDAMENTOS DO PROFESSOR: {all_schedules.count()}")
        
        for schedule in all_schedules:
            self.stdout.write(f"   - ID {schedule.id}: {schedule.scheduled_date} - {schedule.laboratory.name} ({schedule.laboratory.department}) - {schedule.status}")
        
        # ==========================================
        # BUSCAR AGENDAMENTOS DA SEMANA ESPECÍFICA
        # ==========================================
        week_schedules = ScheduleRequest.objects.filter(
            professor=professor,
            scheduled_date__range=[start_of_week, end_of_week]
        ).select_related('laboratory', 'professor')
        
        self.stdout.write(f"\n📅 AGENDAMENTOS NA SEMANA ({start_of_week} a {end_of_week}): {week_schedules.count()}")
        
        if week_schedules.exists():
            for schedule in week_schedules:
                self.stdout.write(f"   ✅ {schedule.scheduled_date} - {schedule.laboratory.name} ({schedule.laboratory.department}) - {schedule.status}")
        else:
            self.stdout.write("   ❌ Nenhum agendamento encontrado nesta semana")
        
        # ==========================================
        # TESTAR FILTROS DE DEPARTAMENTO
        # ==========================================
        self.stdout.write(f"\n🏢 TESTANDO FILTROS DE DEPARTAMENTO:")
        self.stdout.write('-' * 40)
        
        # Listar departamentos disponíveis
        departments = Laboratory.objects.filter(is_active=True).values_list('department', flat=True).distinct()
        self.stdout.write(f"Departamentos disponíveis: {list(departments)}")
        
        # Testar cada departamento
        for dept in departments:
            filtered_schedules = week_schedules.filter(laboratory__department=dept)
            self.stdout.write(f"   - {dept.upper()}: {filtered_schedules.count()} agendamentos")
            
            for schedule in filtered_schedules:
                self.stdout.write(f"     ✅ {schedule.scheduled_date} - {schedule.laboratory.name}")
        
        # Testar filtro 'all'
        all_filtered = week_schedules  # Sem filtro
        self.stdout.write(f"   - ALL: {all_filtered.count()} agendamentos")
        
        # ==========================================
        # SIMULAR A LÓGICA DO DASHBOARD
        # ==========================================
        self.stdout.write(f"\n🎯 SIMULANDO LÓGICA DO DASHBOARD:")
        self.stdout.write('-' * 40)
        
        # Testar com filtro 'all'
        self.test_dashboard_logic(professor, start_of_week, end_of_week, 'all')
        
        # Testar com cada departamento
        for dept in departments:
            self.test_dashboard_logic(professor, start_of_week, end_of_week, dept)
        
        # ==========================================
        # VERIFICAR ESTRUTURA DOS DADOS
        # ==========================================
        self.stdout.write(f"\n🔍 VERIFICANDO ESTRUTURA DOS DADOS:")
        self.stdout.write('-' * 40)
        
        if week_schedules.exists():
            schedule = week_schedules.first()
            self.stdout.write(f"Exemplo de agendamento (ID {schedule.id}):")
            self.stdout.write(f"   - Professor: {schedule.professor.get_full_name()}")
            self.stdout.write(f"   - Professor ID: {schedule.professor.id}")
            self.stdout.write(f"   - Laboratório: {schedule.laboratory.name}")
            self.stdout.write(f"   - Lab ID: {schedule.laboratory.id}")
            self.stdout.write(f"   - Departamento: {schedule.laboratory.department}")
            self.stdout.write(f"   - Data: {schedule.scheduled_date}")
            self.stdout.write(f"   - Horário: {schedule.start_time} - {schedule.end_time}")
            self.stdout.write(f"   - Status: {schedule.status}")
            self.stdout.write(f"   - Disciplina: {schedule.subject}")
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ DEBUG DO CALENDÁRIO CONCLUÍDO'))
    
    def test_dashboard_logic(self, professor, start_of_week, end_of_week, department_filter):
        """Simula exatamente a lógica do dashboard"""
        self.stdout.write(f"\n   🧪 Testando filtro: {department_filter}")
        
        # Query base (igual ao dashboard)
        appointments_base = ScheduleRequest.objects.select_related(
            'professor', 
            'laboratory',
            'reviewed_by'
        ).filter(
            scheduled_date__range=[start_of_week, end_of_week],
            professor=professor
        )
        
        # Aplicar filtro de departamento (igual ao dashboard)
        if department_filter != 'all':
            appointments_base = appointments_base.filter(
                laboratory__department=department_filter
            )
        
        current_week_appointments = list(appointments_base)
        
        self.stdout.write(f"      Resultado: {len(current_week_appointments)} agendamentos")
        
        # Agrupar por data (igual ao dashboard)
        appointments_by_date = {}
        for apt in current_week_appointments:
            date_key = apt.scheduled_date
            if date_key not in appointments_by_date:
                appointments_by_date[date_key] = []
            appointments_by_date[date_key].append(apt)
        
        # Construir dados do calendário (igual ao dashboard)
        calendar_data = []
        for i in range(5):  # Segunda a sexta
            day = start_of_week + timedelta(days=i)
            day_appointments = appointments_by_date.get(day, [])
            
            calendar_data.append({
                'date': day,
                'appointments': day_appointments,
                'has_appointments': len(day_appointments) > 0,
                'appointments_count': len(day_appointments)
            })
            
            if day_appointments:
                self.stdout.write(f"      📅 {day}: {len(day_appointments)} agendamento(s)")
                for apt in day_appointments:
                    self.stdout.write(f"         - {apt.laboratory.name} ({apt.start_time}-{apt.end_time})")
        
        return calendar_data