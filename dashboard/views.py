import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import is_technician, is_professor
from django.utils import timezone
from datetime import timedelta, date # Adicionar date
from scheduling.models import DraftScheduleRequest, ScheduleRequest
from inventory.models import Material
from accounts.models import User
from laboratories.models import Laboratory, Department # Importar Laboratory
from django.db.models import Count, Q, F # Importar F aqui
from django.http import HttpResponse, JsonResponse # Importar JsonResponse
from django.template.loader import render_to_string # Para renderizar partes do template
from django.db.models import Count
from django.db.models.functions import TruncYear, TruncWeek, TruncMonth
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import json
import logging


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
        filtered_labs = get_laboratories_by_department(department_filter)
        current_week_appointments = current_week_appointments.filter(laboratory__in=filtered_labs)
    
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
    if Department.objects.exists():
        departments = Department.objects.filter(is_active=True).values_list('code', flat=True)
    else:
        departments = Laboratory.objects.filter(is_active=True).values_list('department', flat=True).distinct()
    
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

# ADICIONAR/SUBSTITUIR no dashboard/views.py

@login_required
@user_passes_test(is_professor)
def professor_dashboard(request):
    import logging
    logger = logging.getLogger('dashboard')
    
    professor = request.user
    today = timezone.now().date()
    
    logger.info(f"🔍 DASHBOARD ACESSADO - Professor: {professor.get_full_name()} (ID: {professor.id})")
    
    # ==========================================
    # CONFIGURAÇÃO DE FILTROS
    # ==========================================
    department_filter = request.GET.get('department', 'all')
    logger.info(f"🏢 FILTRO DEPARTAMENTO: '{department_filter}'")
    
    # Buscar departamentos únicos dos laboratórios ativos
    if Department.objects.exists():
        departments = Department.objects.filter(is_active=True).values_list('code', flat=True)
    else:
        # Fallback para sistema antigo
        departments = Laboratory.objects.filter(is_active=True).values_list('department', flat=True).distinct()
    
    logger.info(f"🏢 DEPARTAMENTOS DISPONÍVEIS: {list(departments)}")
    
    # ==========================================
    # CONFIGURAÇÃO DA SEMANA
    # ==========================================
    week_offset = int(request.GET.get('week_offset', 0))
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=4)  # Segunda a sexta
    
    logger.info(f"📅 SEMANA: {start_of_week} até {end_of_week} (offset: {week_offset})")
    
    # ==========================================
    # BUSCA DE AGENDAMENTOS
    # ==========================================
    
    # Query base
    appointments_base = ScheduleRequest.objects.select_related(
        'professor', 
        'laboratory',
        'reviewed_by'
    ).filter(
        scheduled_date__range=[start_of_week, end_of_week],
        professor=professor
    )
    
    logger.info(f"📊 AGENDAMENTOS BASE: {appointments_base.count()}")
    
    # Aplicar filtro de departamento
    if department_filter != 'all':
        # Usar a função auxiliar para filtrar laboratórios
        filtered_labs = get_laboratories_by_department(department_filter)
        appointments_base = appointments_base.filter(laboratory__in=filtered_labs)
        logger.info(f"🔍 FILTRO APLICADO: department='{department_filter}'")
    
    current_week_appointments = list(appointments_base)
    logger.info(f"📊 AGENDAMENTOS FINAIS: {len(current_week_appointments)}")
    
    # Debug dos agendamentos encontrados
    for apt in current_week_appointments:
        logger.info(f"   ✅ {apt.scheduled_date} - {apt.laboratory.name} ({apt.laboratory.department}) - {apt.status}")
    
    # ==========================================
    # CONSTRUIR DADOS DO CALENDÁRIO
    # ==========================================
    
    appointments_by_date = {}
    
    # Agrupar por data
    for apt in current_week_appointments:
        date_key = apt.scheduled_date
        if date_key not in appointments_by_date:
            appointments_by_date[date_key] = []
        appointments_by_date[date_key].append(apt)
    
    # Construir estrutura do calendário
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
            logger.info(f"📅 {day}: {len(day_appointments)} agendamento(s)")
    
    # ==========================================
    # VERIFICAR SE É REQUISIÇÃO AJAX
    # ==========================================
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        logger.info(f"📡 REQUISIÇÃO AJAX DETECTADA")
        try:
            # 🔧 IMPORTANTE: Usar o template correto para o professor
            from django.template.loader import render_to_string
            
            calendar_html = render_to_string(
                'partials/calendar_week.html',  # Template para professor
                {
                    'calendar_data': calendar_data,
                    'today': today,
                },
                request=request
            )
            
            response_data = {
                'success': True,
                'calendar_html': calendar_html,
                'calendar_data': [
                    {
                        'date': day['date'].strftime('%Y-%m-%d'),
                        'appointments': [
                            {
                                'id': apt.id,
                                'laboratory_name': apt.laboratory.name,
                                'laboratory_department': apt.laboratory.department,
                                'subject': apt.subject,
                                'start_time': apt.start_time.strftime('%H:%M'),
                                'end_time': apt.end_time.strftime('%H:%M'),
                                'status': apt.status,
                                'status_display': apt.get_status_display(),
                            } for apt in day['appointments']
                        ],
                        'has_appointments': day['has_appointments'],
                        'appointments_count': day['appointments_count']
                    } for day in calendar_data
                ],
                'week_start': start_of_week.strftime('%Y-%m-%d'),
                'week_end': end_of_week.strftime('%Y-%m-%d'),
                'week_offset': week_offset,
                'prev_week_offset': week_offset - 1,
                'next_week_offset': week_offset + 1,
                'department_filter': department_filter,
                'departments': list(departments),
            }
            
            logger.info(f"📤 RESPOSTA AJAX ENVIADA COM SUCESSO")
            logger.info(f"📊 Calendar HTML length: {len(calendar_html)} chars")
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"❌ ERRO AJAX: {str(e)}")
            import traceback
            logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            
            return JsonResponse({
                'success': False,
                'error': 'Erro ao carregar calendário',
                'message': str(e)
            }, status=500)
    
    # ==========================================
    # ESTATÍSTICAS PARA PÁGINA COMPLETA
    # ==========================================
    
    pending_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='pending'
    ).count()
    
    approved_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved'
    ).count()
    
    this_week_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__range=[start_of_week, end_of_week]
    ).count()
    
    total_schedules = ScheduleRequest.objects.filter(
        professor=professor
    ).count()
    
    # Calcular mudança percentual da semana
    previous_week_start = start_of_week - timedelta(weeks=1)
    previous_week_end = end_of_week - timedelta(weeks=1)
    previous_week_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__range=[previous_week_start, previous_week_end]
    ).count()
    
    if previous_week_count > 0:
        week_change = ((this_week_count - previous_week_count) / previous_week_count) * 100
    else:
        week_change = 100 if this_week_count > 0 else 0
    
    # ==========================================
    # DADOS ADICIONAIS
    # ==========================================
    
    # Próximas aulas
    upcoming_classes = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__gte=today
    ).order_by('scheduled_date', 'start_time')[:5]
    
    # Rascunhos
    try:
        from scheduling.models import DraftScheduleRequest
        draft_requests = DraftScheduleRequest.objects.filter(
            professor=professor
        ).order_by('-created_at')[:3]
    except:
        draft_requests = []
    
    # Solicitações recentes
    recent_requests = ScheduleRequest.objects.filter(
        professor=professor
    ).order_by('-request_date')[:5]
    
    # Verificar se é dia de agendamento
    is_scheduling_day = today.weekday() in [3, 4]  # quinta=3, sexta=4
    
    # ==========================================
    # LOG FINAL
    # ==========================================
    logger.info(f"📊 ESTATÍSTICAS FINAIS:")
    logger.info(f"   Pendentes: {pending_count}")
    logger.info(f"   Aprovados: {approved_count}")
    logger.info(f"   Esta semana: {this_week_count}")
    logger.info(f"   Total: {total_schedules}")
    
    # ==========================================
    # CONTEXTO PARA TEMPLATE
    # ==========================================
    context = {
        'calendar_data': calendar_data,
        'week_start': start_of_week,
        'week_end': end_of_week,
        'week_offset': week_offset,
        'prev_week_offset': week_offset - 1,
        'next_week_offset': week_offset + 1,
        
        # Filtro de departamento
        'department_filter': department_filter,
        'departments': departments,
        'current_department': department_filter,
        
        # Estatísticas
        'pending_count': pending_count,
        'approved_count': approved_count,
        'this_week_count': this_week_count,
        'total_schedules': total_schedules,
        'week_change': week_change,
        'upcoming_classes': upcoming_classes,
        'draft_requests': draft_requests,
        'recent_requests': recent_requests,
        
        # Configurações
        'is_scheduling_day': is_scheduling_day,
        'today': today,
    }
    
    logger.info(f"📄 RENDERIZANDO TEMPLATE professor.html")
    return render(request, 'professor.html', context)


# ==========================================
# VIEWS AUXILIARES PARA AS APIs (IMPLEMENTAÇÃO COMPLETA)
# ==========================================

@login_required
def laboratory_availability_api(request):
    """API para disponibilidade dos laboratórios"""
    try:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        from laboratories.models import Laboratory
        laboratories = Laboratory.objects.filter(is_active=True)
        
        week_data = []
        for i in range(5):  # Segunda a sexta
            current_date = week_start + timedelta(days=i)
            
            # Agendamentos aprovados para este dia
            day_schedules = ScheduleRequest.objects.filter(
                scheduled_date=current_date,
                status='approved'
            ).values_list('laboratory_id', flat=True)
            
            total_labs = laboratories.count()
            occupied_labs = len(set(day_schedules))
            labs_available = total_labs - occupied_labs
            
            week_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'dayName': current_date.strftime('%a'),
                'dateFormatted': current_date.strftime('%d/%m'),
                'labsAvailable': labs_available,
                'totalLabs': total_labs,
            })
        
        return JsonResponse({
            'success': True,
            'week': week_data,
            'last_updated': timezone.now().isoformat()
        })
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in laboratory_availability_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_professor)
def professor_stats_api(request):
    """API para estatísticas do professor em tempo real"""
    try:
        professor = request.user
        today = timezone.now().date()
        
        # Calcular estatísticas atuais
        pending_count = ScheduleRequest.objects.filter(
            professor=professor,
            status='pending'
        ).count()
        
        approved_count = ScheduleRequest.objects.filter(
            professor=professor,
            status='approved'
        ).count()
        
        total_count = ScheduleRequest.objects.filter(
            professor=professor
        ).count()
        
        # Agendamentos desta semana
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        this_week_count = ScheduleRequest.objects.filter(
            professor=professor,
            status='approved',
            scheduled_date__range=[week_start, week_end]
        ).count()
        
        # Calcular mudança percentual
        previous_week_start = week_start - timedelta(weeks=1)
        previous_week_end = week_end - timedelta(weeks=1)
        
        previous_week_count = ScheduleRequest.objects.filter(
            professor=professor,
            status='approved',
            scheduled_date__range=[previous_week_start, previous_week_end]
        ).count()
        
        if previous_week_count > 0:
            percentage_change = round(((this_week_count - previous_week_count) / previous_week_count) * 100, 1)
        else:
            percentage_change = 100 if this_week_count > 0 else 0
        
        stats = {
            'pending': pending_count,
            'approved': approved_count,
            'total': total_count,
            'thisWeek': this_week_count,
            'percentageChange': percentage_change,
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'last_updated': timezone.now().isoformat()
        })
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in professor_stats_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_professor)
def upcoming_classes_api(request):
    """API para próximas aulas do professor"""
    try:
        professor = request.user
        today = timezone.now().date()
        
        upcoming = ScheduleRequest.objects.filter(
            professor=professor,
            status='approved',
            scheduled_date__gte=today
        ).select_related('laboratory').order_by('scheduled_date', 'start_time')[:10]
        
        classes_data = []
        for class_item in upcoming:
            classes_data.append({
                'id': class_item.id,
                'date': class_item.scheduled_date.strftime('%d/%m/%Y'),
                'time': f"{class_item.start_time.strftime('%H:%M')} - {class_item.end_time.strftime('%H:%M')}",
                'laboratory': class_item.laboratory.name,
                'subject': class_item.subject,
                'status': class_item.status,
                'statusDisplay': class_item.get_status_display(),
                'students': class_item.number_of_students or 0,
            })
        
        return JsonResponse({
            'success': True,
            'classes': classes_data,
            'count': len(classes_data),
            'last_updated': timezone.now().isoformat()
        })
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in upcoming_classes_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["POST"])
def schedule_conflict_check_api(request):
    """API para verificar conflitos de agendamento"""
    try:
        data = json.loads(request.body)
        
        laboratory_id = data.get('laboratory')
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([laboratory_id, date, start_time, end_time]):
            return JsonResponse({
                'success': False,
                'error': 'Dados incompletos'
            }, status=400)
        
        # Verificar conflitos
        conflicts = ScheduleRequest.objects.filter(
            laboratory_id=laboratory_id,
            scheduled_date=date,
            status='approved'
        ).exclude(
            # Verificar sobreposição de horários
            Q(end_time__lte=start_time) | Q(start_time__gte=end_time)
        ).select_related('professor')
        
        has_conflict = conflicts.exists()
        conflict_list = []
        
        if has_conflict:
            for conflict in conflicts:
                conflict_list.append({
                    'professor': conflict.professor.get_full_name(),
                    'time': f"{conflict.start_time.strftime('%H:%M')} - {conflict.end_time.strftime('%H:%M')}",
                    'subject': conflict.subject,
                })
        
        return JsonResponse({
            'success': True,
            'hasConflict': has_conflict,
            'conflicts': conflict_list
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in schedule_conflict_check_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# VERSÃO CORRIGIDA para dashboard/views.py

@login_required
def notifications_check_api(request):
    """API para verificar notificações"""
    try:
        user = request.user
        
        # Verificar se o usuário é professor
        if not (user.is_authenticated and user.user_type == 'professor'):
            return JsonResponse({
                'success': False,
                'error': 'Acesso negado - apenas professores'
            }, status=403)
        
        # ✅ CORREÇÃO: Usar review_date em vez de updated_at
        # Verificar agendamentos revisados nos últimos 30 minutos
        recent_updates = ScheduleRequest.objects.filter(
            professor=user,
            review_date__gte=timezone.now() - timedelta(minutes=30)
        ).exclude(status='pending').exclude(review_date__isnull=True)
        
        # Verificar agendamentos pendentes
        pending_count = ScheduleRequest.objects.filter(
            professor=user,
            status='pending'
        ).count()
        
        # ✅ CORREÇÃO: Usar review_date em vez de updated_at
        # Verificar agendamentos aprovados hoje
        today = timezone.now().date()
        approved_today = ScheduleRequest.objects.filter(
            professor=user,
            status='approved',
            review_date__date=today
        ).count()
        
        notifications = []
        
        # Adicionar notificações baseadas em updates recentes
        for update in recent_updates:
            if update.status == 'approved':
                notifications.append({
                    'type': 'approval',
                    'message': f'Agendamento aprovado para {update.laboratory.name}',
                    'date': update.review_date.isoformat()  # ✅ CORREÇÃO: review_date
                })
            elif update.status == 'rejected':
                notifications.append({
                    'type': 'rejection',
                    'message': f'Agendamento rejeitado para {update.laboratory.name}',
                    'date': update.review_date.isoformat()  # ✅ CORREÇÃO: review_date
                })
        
        return JsonResponse({
            'success': True,
            'hasNew': len(notifications) > 0,
            'count': len(notifications),
            'notifications': notifications,
            'pendingCount': pending_count,
            'approvedToday': approved_today,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in notifications_check_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def chart_data(request):
    """API para dados de gráficos - VERSÃO CORRIGIDA FINAL"""
    import logging
    logger = logging.getLogger('dashboard')
    
    try:
        period = request.GET.get('period', 'week')
        department = request.GET.get('department', 'all')
        
        logger.info(f"📊 CHART-DATA REQUEST: period={period}, department={department}")
        
        # Validar período
        if period not in ['week', 'month', 'year']:
            return JsonResponse({'error': 'Período inválido'}, status=400)
        
        # Configurar período e data
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(weeks=8)
            end_date = today
            x_axis_title = "Semanas"
        elif period == 'month':
            # 🔧 CORREÇÃO: Cálculo mais preciso para mês
            start_date = today.replace(day=1) - timedelta(days=365)
            end_date = today
            x_axis_title = "Meses"
        else:  # year
            start_date = today.replace(month=1, day=1) - timedelta(days=5*365)
            end_date = today
            x_axis_title = "Anos"
        
        logger.info(f"📅 Período: {start_date} até {end_date}")
        
        # Buscar laboratórios
        laboratories = get_laboratories_by_department(department)
        
        logger.info(f"🏢 Laboratórios: {[lab.name for lab in laboratories]}")
        
        if not laboratories.exists():
            return JsonResponse({
                'labels': [],
                'datasets': [],
                'xAxisTitle': x_axis_title
            })
        
        # 🔧 CORREÇÃO PRINCIPAL: Buscar agendamentos e processar corretamente
        schedules = ScheduleRequest.objects.filter(
            scheduled_date__range=[start_date, end_date],
            status='approved'
        )
        
        if department != 'all':
            schedules = schedules.filter(laboratory__department=department)
        
        logger.info(f"📊 Total de agendamentos encontrados: {schedules.count()}")
        
        # Debug detalhado dos agendamentos
        for schedule in schedules:
            logger.info(f"   📋 {schedule.scheduled_date} - {schedule.laboratory.name} - {schedule.subject}")
        
        # 🔧 CORREÇÃO: Gerar labels baseados no período
        labels = []
        
        if period == 'week':
            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime("Semana %d/%m"))
                current_date += timedelta(weeks=1)
        elif period == 'month':
            # 🔧 CORREÇÃO: Gerar labels mensais corretamente
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                labels.append(current_date.strftime("%b %Y"))
                # Próximo mês
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        else:  # year
            current_year = start_date.year
            while current_year <= end_date.year:
                labels.append(str(current_year))
                current_year += 1
        
        logger.info(f"🏷️ Labels gerados: {len(labels)} -> {labels}")
        
        # 🔧 CORREÇÃO PRINCIPAL: Processar dados por laboratório MANUALMENTE
        data_by_lab = {}
        
        for lab in laboratories:
            # Inicializar array com zeros
            lab_data = [0] * len(labels)
            
            # Buscar agendamentos específicos deste laboratório
            lab_schedules = schedules.filter(laboratory=lab)
            
            logger.info(f"🏗️ Processando {lab.name}: {lab_schedules.count()} agendamentos")
            
            # 🔧 CORREÇÃO: Processar cada agendamento individualmente
            for schedule in lab_schedules:
                schedule_date = schedule.scheduled_date
                
                try:
                    if period == 'week':
                        # Calcular índice da semana
                        weeks_diff = (schedule_date - start_date).days // 7
                        if 0 <= weeks_diff < len(labels):
                            lab_data[weeks_diff] += 1
                            logger.info(f"   ✅ Semana {weeks_diff}: +1 -> {lab_data[weeks_diff]}")
                    
                    elif period == 'month':
                        # 🔧 CORREÇÃO: Calcular índice do mês corretamente
                        start_month = start_date.replace(day=1)
                        schedule_month = schedule_date.replace(day=1)
                        
                        # Diferença em meses
                        months_diff = (schedule_month.year - start_month.year) * 12 + (schedule_month.month - start_month.month)
                        
                        if 0 <= months_diff < len(labels):
                            lab_data[months_diff] += 1
                            logger.info(f"   ✅ {lab.name} - {schedule_date} -> Mês {months_diff} ({labels[months_diff]}): +1 -> {lab_data[months_diff]}")
                        else:
                            logger.warning(f"   ⚠️ {lab.name} - {schedule_date} -> Índice {months_diff} fora do range (0-{len(labels)-1})")
                    
                    else:  # year
                        year_diff = schedule_date.year - start_date.year
                        if 0 <= year_diff < len(labels):
                            lab_data[year_diff] += 1
                            logger.info(f"   ✅ Ano {year_diff}: +1 -> {lab_data[year_diff]}")
                
                except Exception as e:
                    logger.error(f"   ❌ Erro ao processar agendamento {schedule.id}: {str(e)}")
                    continue
            
            # Armazenar dados do laboratório
            data_by_lab[lab.name] = lab_data
            total = sum(lab_data)
            logger.info(f"🔢 {lab.name} - Total: {total}, Array: {lab_data}")
        
        # 🔧 CORREÇÃO: Construir datasets
        datasets = []
        colors = ['#4a6fa5', '#198754', '#dc3545', '#6610f2', '#fd7e14', '#6c757d']
        
        for idx, (lab_name, lab_data) in enumerate(data_by_lab.items()):
            color_idx = idx % len(colors)
            
            dataset = {
                'label': lab_name,
                'data': lab_data.copy(),  # Usar .copy() para garantir nova lista
                'borderColor': colors[color_idx],
                'backgroundColor': f"{colors[color_idx]}20",
                'tension': 0.3,
                'fill': True
            }
            
            datasets.append(dataset)
            total = sum(lab_data)
            logger.info(f"📈 Dataset criado - {lab_name}: Total={total}, Data={lab_data}")
        
        # Resposta final
        response_data = {
            'labels': labels,
            'datasets': datasets,
            'xAxisTitle': x_axis_title
        }
        
        logger.info(f"📊 RESPOSTA FINAL:")
        logger.info(f"   Labels: {len(labels)}")
        logger.info(f"   Datasets: {len(datasets)}")
        for i, dataset in enumerate(datasets):
            total = sum(dataset['data'])
            logger.info(f"   Dataset {i} ({dataset['label']}): Total={total}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ ERRO CHART-DATA: {str(e)}")
        import traceback
        logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
        
        return JsonResponse({
            'error': f'Erro interno: {str(e)}'
        }, status=500)

@login_required
def lab_specific_availability_api(request, lab_id):
    """API para disponibilidade específica de um laboratório"""
    try:
        date = request.GET.get('date')
        
        if not date:
            return JsonResponse({
                'success': False,
                'error': 'Data não fornecida'
            }, status=400)
        
        from laboratories.models import Laboratory
        try:
            lab = Laboratory.objects.get(id=lab_id, is_active=True)
        except Laboratory.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Laboratório não encontrado'
            }, status=404)
        
        # Buscar agendamentos para este laboratório nesta data
        existing_schedules = ScheduleRequest.objects.filter(
            laboratory=lab,
            scheduled_date=date,
            status='approved'
        ).order_by('start_time')
        
        # Gerar slots de tempo disponíveis (das 7h às 18h)
        from datetime import time
        
        time_slots = []
        start_hour = 7
        end_hour = 18
        
        for hour in range(start_hour, end_hour):
            slot_start = time(hour, 0)
            slot_end = time(hour + 1, 0)
            
            # Verificar se há conflito com agendamentos existentes
            has_conflict = existing_schedules.filter(
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()
            
            time_slots.append({
                'start': slot_start.strftime('%H:%M'),
                'end': slot_end.strftime('%H:%M'),
                'available': not has_conflict
            })
        
        return JsonResponse({
            'success': True,
            'laboratory': {
                'id': lab.id,
                'name': lab.name,
                'department': lab.department
            },
            'date': date,
            'timeSlots': time_slots,
            'existingSchedules': list(existing_schedules.values(
                'start_time', 'end_time', 'professor__first_name', 
                'professor__last_name', 'subject'
            )),
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in lab_specific_availability_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
def get_laboratories_by_department(department_filter):
    """
    Função auxiliar para filtrar laboratórios por departamento
    Compatível com sistema antigo e novo
    """
    from laboratories.models import Laboratory
    
    laboratories = Laboratory.objects.filter(is_active=True)
    
    if department_filter != 'all':
        # Tentar filtro novo primeiro (múltiplos departamentos)
        new_filter = laboratories.filter(departments__code=department_filter).distinct()
        
        if new_filter.exists():
            return new_filter
        else:
            # Fallback para sistema antigo
            return laboratories.filter(department=department_filter)
    
    return laboratories
    