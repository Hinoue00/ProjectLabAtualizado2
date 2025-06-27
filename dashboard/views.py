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

@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    # Obter parâmetros GET para filtro e navegação
    week_offset = int(request.GET.get('week_offset', 0))
    department_filter = request.GET.get('department', 'all')

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
        scheduled_date__range=[start_of_week, end_of_week]
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
                'end_time',
                'status',
                'scheduled_date',
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
    # Ou, se você quiser manter a capitalização original mas ainda eliminar duplicatas:
    departments = list(dict.fromkeys(Laboratory.objects.values_list('department', flat=True)))

    # Calcular dados para os cards de estatísticas
    actual_start_of_week = today - timedelta(days=today.weekday())
    actual_end_of_week = actual_start_of_week + timedelta(days=6)
    prev_actual_start_of_week = actual_start_of_week - timedelta(days=7)
    prev_actual_end_of_week = actual_end_of_week - timedelta(days=7)

    # Para estatísticas de uso real (mantém o filtro approved):
    actual_week_stats = ScheduleRequest.objects.filter(
        scheduled_date__range=[actual_start_of_week, actual_end_of_week],
        status='approved'  # Mantém aqui pois são estatísticas de uso real
    )

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