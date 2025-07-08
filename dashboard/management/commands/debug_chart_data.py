from django.core.management.base import BaseCommand
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear
from datetime import datetime, timedelta
from scheduling.models import ScheduleRequest
from laboratories.models import Laboratory

class Command(BaseCommand):
    help = 'Debug da API chart-data'
    
    def add_arguments(self, parser):
        parser.add_argument('--period', type=str, default='month', help='Período para testar (week, month, year)')
        parser.add_argument('--department', type=str, default='all', help='Departamento para filtrar')
    
    def handle(self, *args, **options):
        period = options['period']
        department = options['department']
        
        self.stdout.write(f"🔍 TESTANDO CHART-DATA: period={period}, department={department}")
        self.stdout.write("=" * 60)
        
        try:
            # Simular exatamente a lógica da view chart_data
            result = self.simulate_chart_data(period, department)
            self.stdout.write(self.style.SUCCESS("✅ Simulação SUCESSO"))
            self.stdout.write(f"Labels: {len(result['labels'])}")
            self.stdout.write(f"Datasets: {len(result['datasets'])}")
            
            for i, dataset in enumerate(result['datasets']):
                self.stdout.write(f"  Dataset {i}: {dataset['label']} - {len(dataset['data'])} pontos")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ ERRO: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())

        self.debug_month_processing()
    
    def simulate_chart_data(self, period, department):
        """Simula exatamente a lógica da view chart_data"""
        
        # Configurar período
        today = timezone.now().date()
        
        if period == 'week':
            # Últimas 8 semanas
            start_date = today - timedelta(weeks=8)
            end_date = today
            trunc_func = TruncWeek
            date_format = "Semana %d/%m"
        elif period == 'month':
            # Últimos 12 meses
            start_date = today.replace(day=1) - timedelta(days=365)
            end_date = today
            trunc_func = TruncMonth
            date_format = "%b %Y"
        else:  # year
            # Últimos 5 anos
            start_date = today.replace(month=1, day=1) - timedelta(days=5*365)
            end_date = today
            trunc_func = TruncYear
            date_format = "%Y"
        
        self.stdout.write(f"📅 Período: {start_date} até {end_date}")
        
        # Buscar laboratórios
        laboratories = Laboratory.objects.filter(is_active=True)
        if department != 'all':
            laboratories = laboratories.filter(department=department)
        
        self.stdout.write(f"🏢 Laboratórios encontrados: {laboratories.count()}")
        for lab in laboratories:
            self.stdout.write(f"   - {lab.name} ({lab.department})")
        
        # Buscar agendamentos
        schedules = ScheduleRequest.objects.filter(
            scheduled_date__range=[start_date, end_date],
            status='approved'
        )
        
        if department != 'all':
            schedules = schedules.filter(laboratory__department=department)
        
        self.stdout.write(f"📊 Agendamentos encontrados: {schedules.count()}")
        
        # Agrupar por período e laboratório
        grouped_data = schedules.values('laboratory__name').annotate(
            period=trunc_func('scheduled_date'),
            count=Count('id')
        ).order_by('period', 'laboratory__name')
        
        self.stdout.write(f"📈 Dados agrupados: {len(grouped_data)} grupos")
        for group in grouped_data[:10]:  # Mostrar apenas os primeiros 10
            self.stdout.write(f"   - {group['laboratory__name']}: {group['period']} = {group['count']}")
        
        if len(grouped_data) > 10:
            self.stdout.write(f"   ... e mais {len(grouped_data) - 10} grupos")
        
        # Gerar labels baseados no período
        if period == 'week':
            labels = []
            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime(date_format))
                current_date += timedelta(weeks=1)
        elif period == 'month':
            labels = []
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                labels.append(current_date.strftime(date_format))
                # Próximo mês
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        else:  # year
            labels = []
            current_year = start_date.year
            while current_year <= end_date.year:
                labels.append(str(current_year))
                current_year += 1
        
        self.stdout.write(f"🏷️ Labels gerados: {len(labels)}")
        self.stdout.write(f"   {labels}")
        
        # Preparar dados por laboratório
        data_by_lab = {}
        for lab in laboratories:
            data_by_lab[lab.name] = [0] * len(labels)
        
        # Preencher dados
        for group in grouped_data:
            lab_name = group['laboratory__name']
            period_date = group['period']
            count = group['count']
            
            if lab_name in data_by_lab:
                # Encontrar índice correto baseado no período
                if period == 'week':
                    # Calcular semanas desde start_date
                    weeks_diff = (period_date.date() - start_date).days // 7
                    if 0 <= weeks_diff < len(labels):
                        data_by_lab[lab_name][weeks_diff] = count
                elif period == 'month':
                    # Calcular diferença em meses
                    months_diff = (period_date.year - start_date.year) * 12 + (period_date.month - start_date.month)
                    if 0 <= months_diff < len(labels):
                        data_by_lab[lab_name][months_diff] = count
                else:  # year
                    year_diff = period_date.year - start_date.year
                    if 0 <= year_diff < len(labels):
                        data_by_lab[lab_name][year_diff] = count
        
        # Construir datasets
        datasets = []
        colors = ['#4a6fa5', '#198754', '#dc3545', '#6610f2', '#fd7e14', '#6c757d']
        
        for idx, (lab_name, lab_data) in enumerate(data_by_lab.items()):
            color_idx = idx % len(colors)
            datasets.append({
                'label': lab_name,
                'data': lab_data,
                'borderColor': colors[color_idx],
                'backgroundColor': f"{colors[color_idx]}20",
                'tension': 0.3,
                'fill': True
            })
        
        self.stdout.write(f"📊 Datasets criados: {len(datasets)}")
        for dataset in datasets:
            self.stdout.write(f"   - {dataset['label']}: {dataset['data']}")
        
        return {
            'labels': labels,
            'datasets': datasets,
            'xAxisTitle': f'Período ({period})'
        }
    
    def debug_month_processing(self):
        """Debug específico do processamento mensal"""
        self.stdout.write("🔍 DEBUG ESPECÍFICO DO PROCESSAMENTO MENSAL")
        self.stdout.write("=" * 50)
        
        from scheduling.models import ScheduleRequest
        from laboratories.models import Laboratory
        
        # Buscar agendamento específico que deveria aparecer
        schedules = ScheduleRequest.objects.filter(status='approved')
        
        self.stdout.write(f"📊 Agendamentos aprovados: {schedules.count()}")
        
        for schedule in schedules:
            self.stdout.write(f"   📋 ID {schedule.id}:")
            self.stdout.write(f"      Data: {schedule.scheduled_date}")
            self.stdout.write(f"      Lab: {schedule.laboratory.name}")
            self.stdout.write(f"      Professor: {schedule.professor.get_full_name()}")
            self.stdout.write(f"      Status: {schedule.status}")
            
            # Calcular em que mês deveria aparecer
            today = timezone.now().date()
            start_date = today.replace(day=1) - timedelta(days=365)
            start_month = start_date.replace(day=1)
            schedule_month = schedule.scheduled_date.replace(day=1)
            
            months_diff = (schedule_month.year - start_month.year) * 12 + (schedule_month.month - start_month.month)
            
            self.stdout.write(f"      Deveria aparecer no índice: {months_diff}")
            
            # Gerar labels para verificar
            labels = []
            current_date = start_date.replace(day=1)
            end_date = today
            
            while current_date <= end_date:
                labels.append(current_date.strftime("%b %Y"))
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            if 0 <= months_diff < len(labels):
                self.stdout.write(f"      Label correspondente: {labels[months_diff]}")
            else:
                self.stdout.write(f"      ❌ ÍNDICE FORA DO RANGE! (0-{len(labels)-1})")