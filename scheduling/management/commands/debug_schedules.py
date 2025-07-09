"""
Para rodar: python manage.py debug_schedules
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from scheduling.models import ScheduleRequest, Laboratory
from accounts.models import User

class Command(BaseCommand):
    help = 'Debug de agendamentos no sistema'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 INICIANDO DEBUG DOS AGENDAMENTOS'))
        
        # Verificar laboratórios
        labs = Laboratory.objects.all()
        self.stdout.write(f"🏢 LABORATÓRIOS ENCONTRADOS: {labs.count()}")
        for lab in labs:
            self.stdout.write(f"   - {lab.name} ({lab.department}) - Ativo: {lab.is_active}")
        
        # Verificar professores
        professors = User.objects.filter(user_type='professor', is_approved=True)
        self.stdout.write(f"👨‍🏫 PROFESSORES ATIVOS: {professors.count()}")
        
        # Verificar agendamentos
        schedules = ScheduleRequest.objects.all()
        self.stdout.write(f"📅 TOTAL DE AGENDAMENTOS: {schedules.count()}")
        
        # Por status
        for status, _ in ScheduleRequest.STATUS_CHOICES:
            count = schedules.filter(status=status).count()
            self.stdout.write(f"   - {status.upper()}: {count}")
        
        # Por departamento
        self.stdout.write(f"📊 AGENDAMENTOS POR DEPARTAMENTO:")
        for dept, _ in Laboratory.DEPARTMENT_CHOICES:
            count = schedules.filter(laboratory__department=dept).count()
            self.stdout.write(f"   - {dept.upper()}: {count}")
        
        # Últimos 5 agendamentos
        recent = schedules.order_by('-request_date')[:5]
        self.stdout.write(f"🕐 ÚLTIMOS AGENDAMENTOS:")
        for schedule in recent:
            self.stdout.write(f"   - ID {schedule.pk}: {schedule.professor.get_full_name()} - {schedule.laboratory.name} - {schedule.status}")
        
        self.stdout.write(self.style.SUCCESS('✅ DEBUG CONCLUÍDO'))