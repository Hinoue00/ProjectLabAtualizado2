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
from django.http import HttpResponse, JsonResponse # Importar JsonResponse
from django.template.loader import render_to_string # Para renderizar partes do template
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import json


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

    # ==========================================
    # DADOS PARA ESTATÍSTICAS (Stats Cards)
    # ==========================================
    
    # Agendamentos pendentes do professor
    pending_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='pending'
    ).count()
    
    # Agendamentos aprovados do professor
    approved_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved'
    ).count()
    
    # Agendamentos desta semana (aprovados)
    this_week_count = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__range=[start_of_week, end_of_week]
    ).count()
    
    # Total de agendamentos do professor
    total_schedules = ScheduleRequest.objects.filter(
        professor=professor
    ).count()
    
    # Calcular mudança percentual da semana (para o badge)
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
    # DADOS PARA PRÓXIMAS AULAS
    # ==========================================
    
    # Upcoming approved lab reservations
    upcoming_classes = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__gte=today
    ).select_related('laboratory').order_by('scheduled_date', 'start_time')

    # ==========================================
    # DADOS PARA RASCUNHOS
    # ==========================================
    
    # Add draft requests
    draft_requests = DraftScheduleRequest.objects.filter(
        professor=professor
    ).select_related('laboratory').order_by('-created_at')

    # ==========================================
    # DADOS PARA HISTÓRICO RECENTE
    # ==========================================
    
    # Recent requests (últimos agendamentos independente do status)
    recent_requests = ScheduleRequest.objects.filter(
        professor=professor
    ).select_related('laboratory').order_by('-request_date')[:10]

    # ==========================================
    # DADOS PARA DISPONIBILIDADE DA SEMANA
    # ==========================================
    
    # Verificar se hoje é quinta ou sexta (para mostrar botão de agendamento)
    is_scheduling_day = today.weekday() in [3, 4]  # 3=Thursday, 4=Friday
    
    # Buscar laboratórios disponíveis para calcular disponibilidade
    from laboratories.models import Laboratory
    laboratories = Laboratory.objects.filter(is_active=True)
    
    # Criar dados de disponibilidade para cada dia da semana
    week_availability = []
    for i in range(5):  # Segunda a sexta
        current_date = start_of_week + timedelta(days=i)
        
        # Buscar agendamentos aprovados para este dia
        day_schedules = ScheduleRequest.objects.filter(
            scheduled_date=current_date,
            status='approved'
        ).values_list('laboratory_id', flat=True)
        
        # Calcular laboratórios disponíveis
        total_labs = laboratories.count()
        occupied_labs = len(set(day_schedules))  # Labs únicos ocupados
        labs_available = total_labs - occupied_labs
        
        # Determinar status da disponibilidade
        if labs_available == 0:
            status_class = 'unavailable'
            status_text = 'Indisponível'
        elif labs_available == total_labs:
            status_class = 'available'
            status_text = 'Disponível'
        else:
            status_class = 'partial'
            status_text = f'{labs_available}/{total_labs} disponível'
        
        week_availability.append({
            'date': current_date,
            'day_name': current_date.strftime('%a'),
            'labs_available': labs_available,
            'total_labs': total_labs,
            'status_class': status_class,
            'status_text': status_text,
        })

    # ==========================================
    # DADOS PARA CALENDÁRIO SEMANAL
    # ==========================================
    
    # Fetch the professor's approved schedule requests for the week
    week_appointments = ScheduleRequest.objects.filter(
        professor=professor,
        scheduled_date__range=[start_of_week, end_of_week],
    ).select_related('laboratory')

    # Organize calendar data (mantém compatibilidade com template atual)
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
                'subject',
                'status',
                'number_of_students',
                'materials',  # CORRIGIDO: era 'required_materials'
                'description'
            ))
        }
        calendar_data.append(day_data)

    # ==========================================
    # CONTEXT FINAL OTIMIZADO
    # ==========================================
    
    context = {
        # ===== DADOS BÁSICOS =====
        'user': professor,
        'today': today,
        
        # ===== DADOS DE AGENDAMENTO =====
        'is_scheduling_day': is_scheduling_day,
        
        # ===== ESTATÍSTICAS (Stats Cards) =====
        'pending_count': pending_count,
        'approved_count': approved_count,
        'this_week_count': this_week_count,
        'total_schedules': total_schedules,
        'week_change': round(week_change, 1),  # Arredondar para 1 casa decimal
        
        # ===== DADOS DA SEMANA =====
        'week_start': start_of_week,
        'week_end': end_of_week,
        'week_offset': week_offset,
        'prev_week_offset': week_offset - 1,
        'next_week_offset': week_offset + 1,
        
        # ===== DISPONIBILIDADE =====
        'week_availability': week_availability,
        
        # ===== LISTAS DE DADOS =====
        'upcoming_classes': upcoming_classes,  # Mantém nome original do template
        'draft_requests': draft_requests,
        'recent_requests': recent_requests,
        'laboratories': laboratories,  # Para modal de agendamento
        
        # ===== CALENDÁRIO (Compatibilidade) =====
        'calendar_data': calendar_data,
        'current_week_start': start_of_week,  # Alias para compatibilidade
        'current_week_end': end_of_week,      # Alias para compatibilidade
        
        # ===== ALIASES PARA COMPATIBILIDADE COM TEMPLATE ATUAL =====
        'upcoming_reservations': upcoming_classes,  # Template usa este nome
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
    }
    
    # ==========================================
    # SUPORTE AJAX PARA NAVEGAÇÃO DO CALENDÁRIO
    # ==========================================
    
    # Verificar se é uma requisição AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"AJAX Request - week_offset: {week_offset}")
            logger.info(f"Calendar data length: {len(calendar_data)}")
            
            # Verificar se o template existe
            import os
            from django.conf import settings
            template_path = os.path.join(settings.BASE_DIR, 'dashboard', 'templates', 'partials', 'calendar_week.html')
            logger.info(f"Template exists: {os.path.exists(template_path)}")
            
            # Renderizar apenas o HTML do calendário
            from django.template.loader import render_to_string
            
            calendar_html = render_to_string(
                'partials/calendar_week.html',
                {
                    'calendar_data': calendar_data,
                    'today': today,
                },
                request=request
            )
            
            logger.info(f"Calendar HTML length: {len(calendar_html)}")
            
            # Retornar JSON com o HTML
            response_data = {
                'success': True,
                'calendar_html': calendar_html,
                'week_offset': week_offset,
                'start_of_week': start_of_week.strftime('%Y-%m-%d'),
                'end_of_week': end_of_week.strftime('%Y-%m-%d'),
                'debug_info': {
                    'calendar_data_count': len(calendar_data),
                    'today': today.strftime('%Y-%m-%d'),
                    'template_rendered': True
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"AJAX Calendar Error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return JsonResponse({
                'success': False,
                'error': 'Erro ao carregar calendário',
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=500)
    
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

@login_required
def notifications_check_api(request):
    """API para verificar notificações"""
    try:
        user = request.user
        
        # Verificar agendamentos atualizados nos últimos 30 minutos
        recent_updates = ScheduleRequest.objects.filter(
            professor=user,
            updated_at__gte=timezone.now() - timedelta(minutes=30)
        ).exclude(status='pending')
        
        # Verificar agendamentos pendentes
        pending_count = ScheduleRequest.objects.filter(
            professor=user,
            status='pending'
        ).count()
        
        # Verificar agendamentos aprovados hoje
        today = timezone.now().date()
        approved_today = ScheduleRequest.objects.filter(
            professor=user,
            status='approved',
            updated_at__date=today
        ).count()
        
        notifications = []
        
        # Adicionar notificações baseadas em updates recentes
        for update in recent_updates:
            if update.status == 'approved':
                notifications.append({
                    'type': 'approval',
                    'message': f'Agendamento aprovado para {update.laboratory.name}',
                    'date': update.updated_at.isoformat()
                })
            elif update.status == 'rejected':
                notifications.append({
                    'type': 'rejection',
                    'message': f'Agendamento rejeitado para {update.laboratory.name}',
                    'date': update.updated_at.isoformat()
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