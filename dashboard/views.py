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

@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    # Obter parâmetros GET para filtro e navegação
    week_offset = int(request.GET.get('week_offset', 0))
    department_filter = request.GET.get('department', None)

    # Calcular datas da semana com base no offset
    today = timezone.now().date()
    # Ir para o início da semana (segunda-feira) e aplicar o offset
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=4) # Considerando Segunda a Sexta

    # Datas da semana anterior e próxima para navegação
    prev_week_offset = week_offset - 1
    next_week_offset = week_offset + 1

    # Filtrar agendamentos para a semana selecionada
    appointments_query = ScheduleRequest.objects.filter(
        scheduled_date__range=[start_of_week, end_of_week],
        status='approved'
    )

    # Aplicar filtro de departamento se selecionado
    if department_filter and department_filter != 'all':
        appointments_query = appointments_query.filter(laboratory__department=department_filter)

    current_week_appointments = appointments_query.select_related('professor', 'laboratory')

    # Organizar dados do calendário para a semana selecionada (Segunda a Sexta)
    calendar_data = []
    for i in range(5):
        day = start_of_week + timedelta(days=i)
        # Filtrar os agendamentos já buscados para este dia específico
        day_appointments = current_week_appointments.filter(scheduled_date=day)
        calendar_data.append({
            'date': day,
            'is_today': day == today, # Marcar o dia atual
            'appointments': list(day_appointments.values( # Serializar dados básicos para JSON
                'id',
                'professor__first_name',
                'professor__last_name',
                'laboratory__name',
                'start_time',
                'end_time'
            ))
        })

    # Verificar se é uma requisição AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        # Renderizar apenas a parte do calendário como HTML
        calendar_html = render_to_string(
            'partials/calendar_week.html', # Criaremos este template parcial
            {
                'calendar_data': calendar_data,
                'today': today,
            },
            request=request
        )
        return JsonResponse({
            'calendar_html': calendar_html,
            'start_of_week': start_of_week.isoformat(),
            'end_of_week': end_of_week.isoformat(),
            'week_offset': week_offset,
            'prev_week_offset': prev_week_offset,
            'next_week_offset': next_week_offset,
        })

    # --- Lógica original para carregamento completo da página ---
    # Obter departamentos distintos dos laboratórios para o filtro
    departments = Laboratory.objects.values_list('department', flat=True).distinct()

    # Calcular dados para os cards de estatísticas
    actual_start_of_week = today - timedelta(days=today.weekday())
    actual_end_of_week = actual_start_of_week + timedelta(days=6)
    prev_actual_start_of_week = actual_start_of_week - timedelta(days=7)
    prev_actual_end_of_week = actual_end_of_week - timedelta(days=7)

    current_actual_week_appointments = ScheduleRequest.objects.filter(
        scheduled_date__range=[actual_start_of_week, actual_end_of_week],
        status='approved'
    )
    previous_actual_week_appointments = ScheduleRequest.objects.filter(
        scheduled_date__range=[prev_actual_start_of_week, prev_actual_end_of_week],
        status='approved'
    )
    current_count = current_actual_week_appointments.count()
    previous_count = previous_actual_week_appointments.count()
    percentage_change = ((current_count - previous_count) / previous_count) * 100 if previous_count > 0 else (100 if current_count > 0 else 0)

    pending_approvals = User.objects.filter(is_approved=False).count()
    pending_appointments_qs = ScheduleRequest.objects.filter(status='pending')
    pending_appointments_count = pending_appointments_qs.count()
    pending_appointment_objects = pending_appointments_qs.order_by('scheduled_date')[:5]

    materials_in_alert = Material.objects.filter(quantity__lte=F('minimum_stock'))
    active_professors = User.objects.filter(
        user_type='professor',
        schedulerequest__status='approved',
        schedulerequest__scheduled_date__gte=today
    ).distinct()
    recent_appointments = ScheduleRequest.objects.filter(
        status__in=['approved', 'rejected']
    ).order_by('-review_date')[:10]

    context = {
        'current_week_appointments': current_week_appointments, # Usado apenas no render completo
        'current_count': current_count,
        'percentage_change': percentage_change,
        'pending_approvals': pending_approvals,
        'pending_appointments': pending_appointments_count, # Passar a contagem
        'pending_appointment_objects': pending_appointment_objects,
        'materials_in_alert': materials_in_alert,
        'active_professors': active_professors,
        'calendar_data': calendar_data, # Passar para o render completo também
        'recent_appointments': recent_appointments,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'week_offset': week_offset,
        'prev_week_offset': prev_week_offset,
        'next_week_offset': next_week_offset,
        'departments': departments,
        'current_department': department_filter,
        'today': today,
    }

    return render(request, 'technician.html', context)

@login_required
@user_passes_test(is_professor)
def professor_dashboard(request):
    # Get current user
    professor = request.user
    
    # Today's date
    today = timezone.now().date()
    
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
    
    # Calendar days for the current week
    start_of_week = today - timedelta(days=today.weekday())
    calendar_days = []
    
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        # Check if there are events on this day
        has_events = ScheduleRequest.objects.filter(
            professor=professor,
            scheduled_date=day,
            status='approved'
        ).exists()
        
        calendar_days.append({
            'date': day,
            'is_today': day == today,
            'has_events': has_events
        })
    
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
    
    context = {
        'upcoming_reservations': upcoming_reservations,
        'pending_requests': pending_requests,
        'past_reservations': past_reservations,
        'is_scheduling_day': is_scheduling_day,
        'calendar_days': calendar_days,
        'today_events': today_events,
        'today': today,
        'draft_requests': draft_requests,
    }
    
    return render(request, 'professor.html', context)