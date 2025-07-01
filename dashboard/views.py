from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import is_technician, is_professor
from django.utils import timezone
from datetime import timedelta, date # Adicionar date
from scheduling.models import DraftScheduleRequest, ScheduleRequest
from inventory.models import Material
from accounts.models import User
from laboratories.models import Laboratory # Importar Laboratory
from django.db.models import Count, Q, F # Importar F aqui
from django.http import JsonResponse # Importar JsonResponse
from django.template.loader import render_to_string # Para renderizar partes do template
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.core.cache import cache


@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    # Get parameters
    week_offset = int(request.GET.get('week_offset', 0))
    department_filter = request.GET.get('department', 'all')

    # Calculate dates
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=4)
    
    # Query appointments
    appointments_base = ScheduleRequest.objects.select_related(
        'professor', 
        'laboratory',
        'reviewed_by'
    ).filter(
        scheduled_date__range=[start_of_week, end_of_week]
    )
    
    if department_filter != 'all':
        appointments_base = appointments_base.filter(
            laboratory__department=department_filter
        )
    
    current_week_appointments = list(appointments_base)
    
    # Build calendar data
    calendar_data = []
    appointments_by_date = {}
    
    # Group appointments by date
    for apt in current_week_appointments:
        date_key = apt.scheduled_date
        if date_key not in appointments_by_date:
            appointments_by_date[date_key] = []
        appointments_by_date[date_key].append(apt)
    
    # Build calendar structure
    for i in range(5):  # Monday to Friday
        day = start_of_week + timedelta(days=i)
        day_appointments = appointments_by_date.get(day, [])
        
        calendar_data.append({
            'date': day,
            'appointments': day_appointments,
            'has_appointments': len(day_appointments) > 0,
            'appointments_count': len(day_appointments)
        })
    
    # ✅ CHECK FOR AJAX REQUEST
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        try:
            # Render calendar partial template
            calendar_html = render_to_string(
                'partials/calendar_week_technician.html',
                {
                    'calendar_data': calendar_data,
                    'today': today,
                },
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'calendar_html': calendar_html,
                'start_of_week': start_of_week.isoformat(),
                'end_of_week': end_of_week.isoformat(),
                'week_offset': week_offset,
                'prev_week_offset': week_offset - 1,
                'next_week_offset': week_offset + 1,
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AJAX Calendar Error: {str(e)}")
            
            return JsonResponse({
                'success': False,
                'error': 'Erro ao carregar calendário',
                'message': str(e)
            }, status=500)
    
    # Non-AJAX request - full page load
    pending_appointments_count = ScheduleRequest.objects.filter(status='pending').count()
    pending_approvals = User.objects.filter(is_approved=False, is_active=True).count()
    materials_in_alert = Material.objects.filter(quantity__lte=F('minimum_stock'))
    materials_in_alert_count = materials_in_alert.count()
    active_professors = User.objects.filter(user_type='professor', is_approved=True, is_active=True)
    active_professors_count = active_professors.count()
    
    # Calculate percentage change
    last_week_start = start_of_week - timedelta(weeks=1)
    last_week_end = end_of_week - timedelta(weeks=1)
    
    last_week_count = ScheduleRequest.objects.filter(
        scheduled_date__range=[last_week_start, last_week_end],
        status='approved'
    ).count()
    
    current_count = len([apt for apt in current_week_appointments if apt.status == 'approved'])
    
    if last_week_count > 0:
        percentage_change = ((current_count - last_week_count) / last_week_count) * 100
    else:
        percentage_change = 100 if current_count > 0 else 0
    
    # Stats
    stats = {
        'pending_requests': sum(1 for apt in current_week_appointments if apt.status == 'pending'),
        'approved_requests': sum(1 for apt in current_week_appointments if apt.status == 'approved'),
        'total_requests': len(current_week_appointments),
    }
    
    materials_stats = Material.objects.aggregate(
        total_materials=Count('id'),
        materials_in_alert_count=Count('id', filter=Q(quantity__lte=F('minimum_stock'))),
        total_laboratories=Count('laboratory', distinct=True)
    )
    
    stats.update(materials_stats)
    
    recent_requests = ScheduleRequest.objects.select_related(
        'professor', 'laboratory'
    ).order_by('-request_date')[:10]
    
    # Get departments
    from django.core.cache import cache
    departments = cache.get('departments_list')
    if not departments:
        departments = Laboratory.objects.values_list(
            'department', flat=True
        ).distinct().order_by('department')
        cache.set('departments_list', list(departments), 60 * 60)
    
    context = {
        'calendar_data': calendar_data,
        'current_week_start': start_of_week,
        'current_week_end': end_of_week,
        'week_offset': week_offset,
        'prev_week_offset': week_offset - 1,
        'next_week_offset': week_offset + 1,
        'department_filter': department_filter,
        'departments': departments,
        'recent_requests': recent_requests,
        'stats': stats,
        'today': today,
        
        # Stats for template
        'pending_appointments': pending_appointments_count,
        'pending_approvals': pending_approvals,
        'materials_in_alert': materials_in_alert,
        'materials_in_alert_count': materials_in_alert_count,
        'active_professors': active_professors,
        'active_professors_count': active_professors_count,
        'current_count': current_count,
        'percentage_change': percentage_change,
        
        # Compatibility
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'current_department': department_filter,
    }
    
    return render(request, 'technician.html', context)

@login_required
@user_passes_test(is_professor)
def professor_dashboard(request):
    # Obter parâmetros GET para navegação
    week_offset = int(request.GET.get('week_offset', 0))
    
    # Define today first
    today = timezone.now().date()

    # Get current user
    professor = request.user

    # Calcular datas da semana com base no offset
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=4)  # Até sexta-feira

    # Upcoming approved lab reservations
    upcoming_reservations = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__gte=today
    ).order_by('scheduled_date')

    # Pending requests
    pending_requests = ScheduleRequest.objects.filter(
        professor=professor,
        status='pending'
    ).order_by('scheduled_date')

    # Past reservations
    past_reservations = ScheduleRequest.objects.filter(
        professor=professor,
        scheduled_date__lt=today
    ).order_by('-scheduled_date')[:10]

    # Check if today is Thursday or Friday (for showing scheduling button)
    is_scheduling_day = today.weekday() in [3, 4]  # 3=Thursday, 4=Friday

    # Today's events
    today_events = ScheduleRequest.objects.filter(
        professor=professor,
        scheduled_date=today,
        status='approved'
    ).order_by('start_time')

    # Add draft requests
    draft_requests = DraftScheduleRequest.objects.filter(
        professor=request.user
    ).order_by('scheduled_date')

    # Fetch the professor's approved schedule requests for the week
    week_appointments = ScheduleRequest.objects.filter(
        professor=request.user,
        scheduled_date__range=[start_of_week, end_of_week],
    ).select_related('laboratory')

    # Organize calendar data
    calendar_data = []
    for i in range(5):  # Monday to Friday
        current_day = start_of_week + timedelta(days=i)

        # Filter appointments for this specific day
        day_appointments = week_appointments.filter(scheduled_date=current_day)

        day_data = {
            'date': current_day,
            'is_today': current_day == today,
            'appointments': list(day_appointments.values(
                'id',
                'professor__first_name',
                'professor__last_name',
                'laboratory__name',
                'start_time',
                'end_time',
                'scheduled_date',
                'status',
            ))
        }
        calendar_data.append(day_data)

    context = {
        'upcoming_reservations': upcoming_reservations,
        'pending_requests': pending_requests,
        'past_reservations': past_reservations,
        'is_scheduling_day': is_scheduling_day,
        'today_events': today_events,
        'today': today,
        'draft_requests': draft_requests,
        'calendar_data': calendar_data,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
    }
    
    # Verificar se é uma requisição AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        # Renderizar apenas o HTML do calendário
        calendar_html = render_to_string(
            'partials/calendar_week.html',
            {
                'calendar_data': calendar_data,
                'today': today,
            },
            request=request
        )
        
        # Retornar dados como JSON
        return JsonResponse({
            'calendar_html': calendar_html,
            'start_of_week': start_of_week.isoformat(),
            'end_of_week': end_of_week.isoformat(),
            'week_offset': week_offset,
        })

    return render(request, 'professor.html', context)

@login_required
@user_passes_test(is_technician)
def chart_data(request):
    # Obter parâmetros da requisição
    period = request.GET.get('period', 'week')
    department = request.GET.get('department', 'all')
    
    # Definir datas com base no período
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=today.weekday() + 7)  # 2 semanas atrás, começando segunda
        end_date = today + timedelta(days=6 - today.weekday())  # até domingo da semana atual
        date_trunc = TruncDay  # Agrupar por dia
        labels = [(start_date + timedelta(days=i)).strftime('%d/%m') for i in range((end_date - start_date).days + 1)]
        x_axis_title = 'Dias da Semana'
    elif period == 'month':
        start_date = today.replace(day=1) - timedelta(days=30)  # Aproximadamente 1 mês atrás
        end_date = today.replace(day=1) + timedelta(days=31)  # Aproximadamente 1 mês à frente
        date_trunc = TruncWeek  # Agrupar por semana
        # Gerar rótulos para semanas (ex: "Sem 1", "Sem 2", etc.)
        num_weeks = (end_date - start_date).days // 7 + 1
        labels = [f"Sem {i+1}" for i in range(num_weeks)]
        x_axis_title = 'Semanas do Mês'
    elif period == 'year':
        start_date = today.replace(month=1, day=1)  # Início do ano atual
        end_date = today.replace(month=12, day=31)  # Fim do ano atual
        date_trunc = TruncMonth  # Agrupar por mês
        # Nomes dos meses abreviados
        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        labels = month_names
        x_axis_title = 'Meses do Ano'
    else:
        # Período padrão (semana)
        start_date = today - timedelta(days=today.weekday())  # Início da semana atual
        end_date = start_date + timedelta(days=6)  # Fim da semana atual
        date_trunc = TruncDay  # Agrupar por dia
        labels = [(start_date + timedelta(days=i)).strftime('%a') for i in range(7)]  # Dias da semana abreviados
        x_axis_title = 'Dias da Semana'
    
    # Base query para agendamentos
    query = ScheduleRequest.objects.filter(
        scheduled_date__range=[start_date, end_date],
        status='approved'
    )
    
    # Aplicar filtro de departamento, se especificado
    if department != 'all':
        query = query.filter(laboratory__department=department)
    
    # Obter dados agrupados por laboratório e data
    if period == 'year':
        # Para ano, agregar por mês
        data_by_lab = {}
        labs = Laboratory.objects.filter(is_active=True)
        
        # Se filtro de departamento estiver ativo, filtrar labs
        if department != 'all':
            labs = labs.filter(department=department)
            
        for lab in labs:
            lab_data = [0] * 12  # 12 meses
            
            # Obter agendamentos para este laboratório
            lab_requests = query.filter(laboratory=lab)
            
            # Agrupar por mês
            grouped = lab_requests.annotate(
                month=TruncMonth('scheduled_date')
            ).values('month').annotate(count=Count('id')).order_by('month')
            
            # Preencher os dados agrupados
            for group in grouped:
                month_idx = group['month'].month - 1  # Índice do mês (0-11)
                lab_data[month_idx] = group['count']
            
            data_by_lab[lab.name] = lab_data
    else:
        # Para semana e mês, agrupar conforme date_trunc
        data_by_lab = {}
        labs = Laboratory.objects.filter(is_active=True)
        
        # Se filtro de departamento estiver ativo, filtrar labs
        if department != 'all':
            labs = labs.filter(department=department)
            
        for lab in labs:
            # Inicializar com zeros
            if period == 'week':
                lab_data = [0] * ((end_date - start_date).days + 1)  # Dias no intervalo
            else:  # month
                lab_data = [0] * len(labels)  # Número de semanas
            
            # Obter agendamentos para este laboratório
            lab_requests = query.filter(laboratory=lab)
            
            # Agrupar por período
            grouped = lab_requests.annotate(
                period=date_trunc('scheduled_date')
            ).values('period').annotate(count=Count('id')).order_by('period')
            
            # Preencher os dados agrupados
            for group in grouped:
                if period == 'week':
                    # Calcular o índice com base no número de dias desde a data inicial
                    day_idx = (group['period'] - start_date).days
                    if 0 <= day_idx < len(lab_data):
                        lab_data[day_idx] = group['count']
                else:  # month
                    # Calcular o índice da semana (mais complexo)
                    week_idx = (group['period'].date() - start_date).days // 7
                    if 0 <= week_idx < len(lab_data):
                        lab_data[week_idx] = group['count']
            
            data_by_lab[lab.name] = lab_data
    
    # Construir datasets para o gráfico
    datasets = []
    colors = ['#4a6fa5', '#198754', '#dc3545', '#6610f2', '#fd7e14', '#6c757d']  # Cores para diferentes laboratórios
    
    # Converter data_by_lab para o formato do Chart.js
    for idx, (lab_name, lab_data) in enumerate(data_by_lab.items()):
        color_idx = idx % len(colors)
        datasets.append({
            'label': lab_name,
            'data': lab_data,
            'borderColor': colors[color_idx],
            'backgroundColor': f"{colors[color_idx]}20",  # Versão transparente da cor
            'tension': 0.3,
            'fill': True
        })
    
    # Retornar dados formatados para o Chart.js
    return JsonResponse({
        'labels': labels,
        'datasets': datasets,
        'xAxisTitle': x_axis_title
    })