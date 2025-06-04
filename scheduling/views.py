# scheduling/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import User
from accounts.views import is_technician, is_professor
from .models import Laboratory, ScheduleRequest, DraftScheduleRequest, FileAttachment
from .forms import ScheduleRequestForm
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
from whatsapp.services import WhatsAppNotificationService


@login_required
def schedule_calendar(request):
    """Exibe calendário de agendamentos de laboratórios"""
    user = request.user
    today = timezone.now().date()
    
    # Define o período para visualização (4 semanas)
    start_date = today - timedelta(days=today.weekday())  # Início da semana atual
    end_date = start_date + timedelta(days=28)  # 4 semanas a partir do início
    
    # Filtra agendamentos conforme o tipo de usuário
    if user.user_type == 'professor':
        # Para professores, mostrar apenas seus próprios agendamentos
        schedule_requests = ScheduleRequest.objects.filter(
            professor=user,
            scheduled_date__range=[start_date, end_date],
            status='approved'
        )
    else:
        # Para laboratoristas, mostrar todos os agendamentos
        schedule_requests = ScheduleRequest.objects.filter(
            scheduled_date__range=[start_date, end_date],
            status='approved'
        )
    
    # Obtém todos os laboratórios disponíveis
    laboratories = Laboratory.objects.filter(is_active=True)
    
    # Organiza as datas para o calendário
    calendar_weeks = []
    date_cursor = start_date
    
    # Gera 4 semanas
    for week in range(4):
        week_days = []
        
        # Gera 7 dias para cada semana
        for day in range(7):
            current_date = date_cursor
            date_cursor = date_cursor + timedelta(days=1)
            
            # Filtra agendamentos para este dia
            day_schedules = schedule_requests.filter(scheduled_date=current_date)
            
            week_days.append({
                'date': current_date,
                'is_today': current_date == today,
                'is_past': current_date < today,
                'day_name': current_date.strftime('%a'),
                'schedules': day_schedules
            })
        
        calendar_weeks.append(week_days)
    
    context = {
        'calendar_weeks': calendar_weeks,
        'laboratories': laboratories,
        'today': today,
    }
    
    return render(request, 'calendar.html', context)

@login_required
@user_passes_test(is_professor)
def create_schedule_request(request):
    """
    Cria uma nova solicitação de agendamento de laboratório com regras especiais
    """
    today = timezone.now().date()
    
    # Define datas da próxima semana para o formulário
    next_week_start = today + timedelta(days=(7 - today.weekday()))
    next_week_end = next_week_start + timedelta(days=4)
    
    # Verifica se é quinta ou sexta-feira
    is_confirmation_day = today.weekday() in [3, 4] or settings.ALLOW_SCHEDULING_ANY_DAY  # 3=quinta, 4=sexta 
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES)
        if form.is_valid():
            schedule_request = form.save(commit=False)
            schedule_request.professor = request.user
            
            # Verifica se a data está na próxima semana
            if not (next_week_start <= schedule_request.scheduled_date <= next_week_end):
                messages.error(request, 'Agendamentos só podem ser feitos para a próxima semana.')
                return render(request, 'create_request.html', {
                    'form': form, 
                    'is_confirmation_day': is_confirmation_day
                })
            
           # Se não for quinta/sexta, cria como rascunho
            if not is_confirmation_day:
                # Cria um novo modelo para rascunhos de agendamento
                draft_request = DraftScheduleRequest.objects.create(
                    professor=request.user,
                    laboratory=schedule_request.laboratory,
                    subject=schedule_request.subject,
                    description=schedule_request.description,
                    scheduled_date=schedule_request.scheduled_date,
                    shift=form.cleaned_data['shift'],  # Salva o turno
                    number_of_students=schedule_request.number_of_students,
                    materials=schedule_request.materials,
                    guide_file=schedule_request.guide_file,
                )
                
                # Define os horários baseados no turno
                draft_request.set_times_from_shift()
                draft_request.save()
                
                messages.success(request, 'Solicitação de agendamento salva como rascunho. Você poderá confirmá-la na quinta ou sexta-feira.')
                return redirect('professor_dashboard')
            
            # Se for quinta/sexta, processa normalmente
            # Verifica conflitos de horário
            if schedule_request.is_conflicting():
                messages.error(request, 'Já existe um agendamento aprovado para este laboratório neste horário.')
                return render(request, 'create_request.html', {
                    'form': form, 
                    'is_confirmation_day': is_confirmation_day
                })
            
            schedule_request.save()

            # Process file attachments
            files = request.FILES.getlist('attachments')
            for file in files:
                FileAttachment.objects.create(
                    schedule_request=schedule_request,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type
                )

            # Adicionar: Enviar notificação WhatsApp
            WhatsAppNotificationService.notify_schedule_request(schedule_request)
            
            messages.success(request, 'Solicitação de agendamento enviada com sucesso! Aguarde a aprovação.')
            return redirect('professor_dashboard')
    else:
        form = ScheduleRequestForm()
    
    context = {
        'form': form,
        'next_week_start': next_week_start,
        'next_week_end': next_week_end,
        'is_confirmation_day': is_confirmation_day,
    }
    
    return render(request, 'create_request.html', context)

@login_required
@user_passes_test(is_professor)
def list_draft_schedule_requests(request):
    """
    Lista os rascunhos de agendamento para confirmação
    """
    today = timezone.now().date()
    
    # Verifica se é quinta ou sexta-feira
    if today.weekday() not in [3, 4]:  # 3=quinta, 4=sexta
        messages.warning(request, 'Rascunhos só podem ser confirmados às quintas e sextas-feiras.')
        return redirect('professor_dashboard')
    
    # Busca rascunhos do usuário atual
    draft_requests = DraftScheduleRequest.objects.filter(
        professor=request.user
    ).order_by('scheduled_date')
    
    context = {
        'draft_requests': draft_requests
    }
    
    return render(request, 'draft_requests.html', context)

@login_required
@user_passes_test(is_professor)
def confirm_draft_schedule_request(request, draft_id):
    """
    Confirma um rascunho de agendamento
    """
    today = timezone.now().date()
    
    # Verifica se é quinta ou sexta-feira
    if today.weekday() not in [3, 4] or settings.ALLOW_SCHEDULING_ANY_DAY:  # 3=quinta, 4=sexta
        messages.warning(request, 'Rascunhos só podem ser confirmados às quintas e sextas-feiras.')
        return redirect('professor_dashboard')
    
    draft_request = get_object_or_404(DraftScheduleRequest, id=draft_id, professor=request.user)
    
    # Cria a solicitação real
    schedule_request = ScheduleRequest.objects.create(
        professor=draft_request.professor,
        laboratory=draft_request.laboratory,
        subject=draft_request.subject,
        description=draft_request.description,
        scheduled_date=draft_request.scheduled_date,
        start_time=draft_request.start_time,
        end_time=draft_request.end_time,
        number_of_students=draft_request.number_of_students,
        materials=draft_request.materials,
        guide_file=draft_request.guide_file,
    )
    
    # Verifica conflitos de horário
    if schedule_request.is_conflicting():
        # Se houver conflito, deleta a solicitação e mantém o rascunho
        schedule_request.delete()
        messages.error(request, 'Já existe um agendamento aprovado para este laboratório neste horário.')
        return redirect('list_draft_schedule_requests')
    
    
    # Deleta o rascunho após confirmação
    draft_request.delete()
    
    messages.success(request, 'Solicitação de agendamento enviada com sucesso! Aguarde a aprovação.')
    return redirect('professor_dashboard')

@login_required
@user_passes_test(is_professor)
def delete_draft_schedule_request(request, draft_id):
    """
    Exclui um rascunho de agendamento
    """
    draft_request = get_object_or_404(DraftScheduleRequest, id=draft_id, professor=request.user)
    draft_request.delete()
    
    messages.success(request, 'Rascunho de agendamento excluído com sucesso.')
    return redirect('list_draft_schedule_requests')

@login_required
def schedule_request_detail(request, pk):
    """Exibe detalhes de uma solicitação de agendamento"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    # Verifica se o usuário tem permissão para visualizar
    if request.user.user_type == 'professor' and schedule_request.professor != request.user:
        messages.error(request, 'Você não tem permissão para visualizar esta solicitação.')
        return redirect('professor_dashboard')
    

    
    context = {
        'schedule_request': schedule_request,
    }
    
    return render(request, 'request_detail.html', context)

@login_required
@user_passes_test(is_professor)
def edit_schedule_request(request, pk):
    """Edita uma solicitação de agendamento pendente"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk, professor=request.user)
    
    # Verifica se a solicitação ainda está pendente
    if schedule_request.status != 'pending':
        messages.error(request, 'Apenas solicitações pendentes podem ser editadas.')
        return redirect('schedule_request_detail', pk=pk)
    
    # Verifica se é uma quinta ou sexta-feira
    today = timezone.now().date()
    if today.weekday() not in [3, 4] or settings.ALLOW_SCHEDULING_ANY_DAY:  # 3=quinta, 4=sexta
        messages.warning(request, 'Agendamentos só podem ser modificados às quintas e sextas-feiras.')
        return redirect('schedule_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES, instance=schedule_request)
        if form.is_valid():
            updated_request = form.save(commit=False)
            
            # Verifica conflitos de horário
            if updated_request.is_conflicting():
                messages.error(request, 'Já existe um agendamento aprovado para este laboratório neste horário.')
                return render(request, 'edit_request.html', {'form': form, 'schedule_request': schedule_request})
            
            updated_request.save()
            messages.success(request, 'Solicitação de agendamento atualizada com sucesso!')
            return redirect('schedule_request_detail', pk=pk)
    else:
        form = ScheduleRequestForm(instance=schedule_request)
    
    context = {
        'form': form,
        'schedule_request': schedule_request,
    }
    
    return render(request, 'edit_request.html', context)

@login_required
@user_passes_test(is_professor)
def cancel_schedule_request(request, pk):
    """Cancela uma solicitação de agendamento pendente"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk, professor=request.user)
    
    # Verifica se a solicitação ainda está pendente
    if schedule_request.status != 'pending':
        messages.error(request, 'Apenas solicitações pendentes podem ser canceladas.')
        return redirect('schedule_request_detail', pk=pk)
    
    if request.method == 'POST':
        schedule_request.delete()
        messages.success(request, 'Solicitação de agendamento cancelada com sucesso.')
        return redirect('professor_dashboard')
    
    context = {
        'schedule_request': schedule_request,
    }
    
    return render(request, 'cancel_request.html', context)

@login_required
@user_passes_test(is_technician)
def schedule_requests_list(request):
    """Lista todas as solicitações de agendamento para revisão pelos laboratoristas"""
    # Obtem filtros
    status_filter = request.GET.get('status', 'pending')
    
    # Aplica filtros
    if status_filter == 'all':
        schedule_requests = ScheduleRequest.objects.all()
    else:
        schedule_requests = ScheduleRequest.objects.filter(status=status_filter)
    
    # Organiza por data
    schedule_requests = schedule_requests.order_by('scheduled_date', 'start_time')
    
    context = {
        'schedule_requests': schedule_requests,
        'status_filter': status_filter,
    }
    
    return render(request, 'requests_list.html', context)

@login_required
@user_passes_test(is_technician)
def approve_schedule_request(request, pk):
    """Aprova uma solicitação de agendamento"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    if schedule_request.status != 'pending':
        messages.error(request, 'Esta solicitação já foi processada.')
        return redirect('schedule_requests_list')
    
    if request.method == 'POST':
        # Verifica conflitos de horário
        if schedule_request.is_conflicting():
            messages.error(request, 'Existe conflito de horário com outro agendamento já aprovado.')
            return redirect('schedule_request_detail', pk=pk)
        
        # Aprova a solicitação
        schedule_request.approve(request.user)

        # Adicionar: Enviar notificação WhatsApp
        WhatsAppNotificationService.notify_schedule_approval(schedule_request)
        
        messages.success(request, f'Solicitação de agendamento de {schedule_request.professor.get_full_name()} aprovada com sucesso.')
        return redirect('schedule_requests_list')
    
    context = {
        'schedule_request': schedule_request,
    }
    
    return render(request, 'approve_request.html', context)

@login_required
@user_passes_test(is_technician)
def reject_schedule_request(request, pk):
    """Rejeita uma solicitação de agendamento"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    if schedule_request.status != 'pending':
        messages.error(request, 'Esta solicitação já foi processada.')
        return redirect('schedule_requests_list')
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        # Rejeita a solicitação
        schedule_request.reject(request.user, rejection_reason)

        # Adicionar: Enviar notificação WhatsApp
        WhatsAppNotificationService.notify_schedule_rejection(schedule_request)
        
        messages.success(request, f'Solicitação de agendamento de {schedule_request.professor.get_full_name()} rejeitada com sucesso.')
        return redirect('schedule_requests_list')
    
    context = {
        'schedule_request': schedule_request,
    }
    
    return render(request, 'reject_request.html', context)

@login_required
@user_passes_test(is_professor)
def edit_draft_schedule_request(request, draft_id):
    """
    Edita um rascunho de agendamento
    """
    draft_request = get_object_or_404(DraftScheduleRequest, id=draft_id, professor=request.user)
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES, instance=draft_request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rascunho de agendamento atualizado com sucesso!')
            return redirect('professor_dashboard')
    else:
        form = ScheduleRequestForm(instance=draft_request)
    
    context = {
        'form': form,
        'title': 'Editar Rascunho de Agendamento',
        'is_edit': True,
        'draft_id': draft_id,
    }
    
    return render(request, 'create_request.html', context)


def calendar_data_api(request):
    # Obter parâmetros da requisição
    week_offset = int(request.GET.get('week_offset', 0))
    filter_labs = request.GET.getlist('labs[]', [])
    
    # Determinar período de datas
    today = timezone.now().date()
    start_date = today - timedelta(days=today.weekday())  # Início da semana atual
    
    # Aplicar deslocamento de semanas
    start_date = start_date + timedelta(weeks=week_offset)
    end_date = start_date + timedelta(days=27)  # 4 semanas (28 dias)
    
    # Construir filtro para laboratórios
    lab_filter = {}
    if filter_labs and 'all' not in filter_labs:
        lab_filter['laboratory__id__in'] = filter_labs
    
    # Buscar agendamentos
    schedule_requests = ScheduleRequest.objects.filter(
        scheduled_date__range=[start_date, end_date],
        **lab_filter
    ).select_related('professor', 'laboratory')
    
    # Organizar dados por semanas e dias
    calendar_data = []
    
    # Gerar 4 semanas
    current_date = start_date
    for week in range(4):
        week_data = []
        
        # Gerar 7 dias para cada semana
        for day in range(7):
            day_schedules = []
            
            # Filtrar agendamentos para este dia
            day_requests = schedule_requests.filter(scheduled_date=current_date)
            
            for request in day_requests:
                day_schedules.append({
                    'id': request.id,
                    'professor_name': request.professor.get_full_name(),
                    'laboratory_name': request.laboratory.name,
                    'laboratory_id': request.laboratory.id,
                    'start_time': request.start_time.strftime('%H:%M'),
                    'end_time': request.end_time.strftime('%H:%M'),
                    'subject': request.subject,
                    'status': request.status
                })
            
            week_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day': current_date.day,
                'is_today': current_date == today,
                'is_past': current_date < today,
                'weekday': current_date.weekday(),
                'schedules': day_schedules
            })
            
            current_date += timedelta(days=1)
        
        calendar_data.append(week_data)
    
    # Obter lista de laboratórios para o filtro
    laboratories = Laboratory.objects.filter(is_active=True).values('id', 'name')
    
    return JsonResponse({
        'calendar_weeks': calendar_data,
        'laboratories': list(laboratories),
        'period': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
    })


def schedule_detail_api(request, schedule_id):
    try:
        schedule = ScheduleRequest.objects.select_related(
            'professor', 'laboratory', 'reviewed_by'
        ).get(id=schedule_id)
        
        # Verificar permissões (se o professor só pode ver seus próprios agendamentos)
        if request.user.user_type == 'professor' and schedule.professor != request.user:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        data = {
            'id': schedule.id,
            'status': schedule.status,
            'professor': {
                'id': schedule.professor.id,
                'name': schedule.professor.get_full_name(),
                'email': schedule.professor.email
            },
            'laboratory': {
                'id': schedule.laboratory.id,
                'name': schedule.laboratory.name,
                'location': schedule.laboratory.location
            },
            'date': schedule.scheduled_date.strftime('%Y-%m-%d'),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'subject': schedule.subject,
            'description': schedule.description,
            'materials': schedule.materials,
            'request_date': schedule.request_date.strftime('%Y-%m-%d %H:%M'),
            'number_of_students': schedule.number_of_students
        }
        
        # Adicionar informações de revisão se já foi revisado
        if schedule.reviewed_by:
            data['review'] = {
                'date': schedule.review_date.strftime('%Y-%m-%d %H:%M'),
                'reviewer': schedule.reviewed_by.get_full_name(),
                'rejection_reason': schedule.rejection_reason
            }
            
        # Verificar tipo de usuário atual
        data['user_info'] = {
            'is_technician': request.user.user_type == 'technician',
            'is_professor': request.user.user_type == 'professor',
            'is_owner': schedule.professor == request.user
        }
            
        return JsonResponse(data)
    except ScheduleRequest.DoesNotExist:
        return JsonResponse({'error': 'Agendamento não encontrado'}, status=404)

