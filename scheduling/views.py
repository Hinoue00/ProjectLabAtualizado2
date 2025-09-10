# scheduling/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, time
from accounts.models import User
from accounts.views import is_technician, is_professor
from .models import Laboratory, ScheduleRequest, DraftScheduleRequest, FileAttachment, ScheduleRequestComment
from laboratories.models import Department
from .forms import ScheduleRequestForm, ExceptionScheduleRequestForm
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
from whatsapp.services import WhatsAppNotificationService
from inventory.models import Material
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404, FileResponse
from django.contrib.auth.decorators import login_required
import os
import mimetypes


def invalidate_schedule_caches():
    """Invalida todos os caches relacionados a agendamentos"""
    cache_keys = [
        'pending_requests_list',
        'pending_appointments_count',
    ]
    cache.delete_many(cache_keys)


@login_required
def schedule_calendar(request):
    """Exibe calendário de agendamentos de laboratórios"""
    user = request.user
    today = timezone.localtime().date()
    
    # Define o período para visualização (mês atual + próximos meses)
    start_date = today.replace(day=1) - timedelta(days=31)  # Mês anterior
    end_date = today.replace(day=1) + timedelta(days=62)    # Próximos 2 meses
    
    # Buscar TODOS os status de agendamentos
    if user.user_type == 'professor':
        # Para professores, mostrar apenas seus próprios agendamentos
        schedule_requests = ScheduleRequest.objects.filter(
            professor=user,
            scheduled_date__range=[start_date, end_date]
        ).select_related('professor', 'laboratory')
    else:
        # Para laboratoristas, mostrar todos os agendamentos
        schedule_requests = ScheduleRequest.objects.filter(
            scheduled_date__range=[start_date, end_date]
        ).select_related('professor', 'laboratory')
    
    # Obtém todos os laboratórios disponíveis para os filtros
    laboratories = Laboratory.objects.filter(is_active=True).prefetch_related('departments')
    
    # Obtém todos os departamentos para o filtro
    from laboratories.models import Department
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    # Converter agendamentos para formato JSON - CAMPOS CORRETOS
    events = []
    for schedule in schedule_requests:
        events.append({
            'id': schedule.id,
            'date': schedule.scheduled_date.strftime('%Y-%m-%d'),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'laboratory_id': schedule.laboratory.id,
            'laboratory_name': schedule.laboratory.name,
            'professor_name': schedule.professor.get_full_name(),
            'subject': schedule.subject or 'Não informado',
            'status': schedule.status,  # pending, approved, rejected
            'description': schedule.description or '',
            'number_of_students': schedule.number_of_students or 0,  # CAMPO CORRETO
            'is_exception': schedule.is_exception,  # CAMPO PARA AGENDAMENTOS DE EXCEÇÃO
        })
    
    # Organiza as datas para o calendário (manter compatibilidade)
    calendar_weeks = []
    week_start = start_date
    for week in range(4):
        week_days = []
        for day in range(7):
            current_date = week_start + timedelta(days=(week * 7) + day)
            if current_date > end_date:
                break
            
            # Filtra agendamentos para este dia
            day_schedules = schedule_requests.filter(scheduled_date=current_date)
            
            week_days.append({
                'date': current_date,
                'is_today': current_date == today,
                'is_past': current_date < today,
                'day_name': current_date.strftime('%a'),
                'schedules': day_schedules
            })
        
        if week_days:
            calendar_weeks.append(week_days)
    
    # Verificar se hoje é segunda ou terça para mostrar botão de agendamento
    is_scheduling_day = today.weekday() in [0, 1]  # 0=Monday, 1=Tuesday
    
    # Obter mês e ano atual para o cabeçalho
    current_month_year = today.strftime('%B %Y').title()
    
    # Converter eventos para JSON de forma segura
    import json
    events_json = json.dumps(events, ensure_ascii=False)
    
    context = {
        'calendar_weeks': calendar_weeks,
        'laboratories': laboratories,
        'departments': departments,
        'events': events,
        'events_json': events_json,  # JSON seguro para JavaScript
        'is_scheduling_day': is_scheduling_day,
        'today': today,
        'current_month_year': current_month_year,
        'user': user,
    }
    
    return render(request, 'calendar.html', context)

@login_required
@user_passes_test(is_professor)
def create_schedule_request(request):
    import logging
    logger = logging.getLogger(__name__)
    
    today = timezone.localtime().date()
    logger.info(f"INICIANDO CRIACAO DE AGENDAMENTO - Professor: {request.user.get_full_name()}")
    
    # REGRA IMPLEMENTADA: Rascunhos podem ser criados qualquer dia, para qualquer dia futuro (exceto domingos)
    # Envio direto ou confirmação de rascunho só pode ser feito segundas/terças para semana seguinte
    
    # Data da próxima semana (segunda a sábado) - agendamentos para semana seguinte
    next_week_start = today + timedelta(days=(7 - today.weekday()))
    next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado
    
    # Verificar se é dia de confirmação (ENVIO DIRETO ou CONFIRMAÇÃO DE RASCUNHO)
    is_confirmation_day = today.weekday() in [0, 1]  # Segunda = 0, Terça = 1
    
    # REGRA: Professores podem criar rascunhos qualquer dia, mas só podem ENVIAR/CONFIRMAR na segunda/terça
    
    if request.method == 'POST':
        logger.info(f" PROCESSANDO FORMULÁRIO DE AGENDAMENTO")
        
        # Verificar se o usuário escolheu salvar como rascunho
        save_as_draft = request.POST.get('save_as_draft') == 'true'
        
        # Rascunho apenas quando explicitamente escolhido pelo usuário
        is_draft = save_as_draft
        form = ScheduleRequestForm(request.POST, request.FILES, is_draft=is_draft)
        
        # Atualizar queryset de materiais baseado no laboratório selecionado
        if 'laboratory' in request.POST and request.POST['laboratory']:
            try:
                lab_id = int(request.POST['laboratory'])
                from inventory.models import Material
                form.fields['selected_materials'].queryset = Material.objects.filter(laboratory_id=lab_id)
                logger.info(f" QUERYSET DE MATERIAIS ATUALIZADO PARA LAB {lab_id}")
            except (ValueError, TypeError):
                logger.warning(f" ERRO AO PROCESSAR LAB ID: {request.POST.get('laboratory')}")
        
        if form.is_valid():
            logger.info(f" FORMULÁRIO VÁLIDO")
            
            # Validação específica para envio direto (não rascunho)
            if not is_draft:
                # REGRA: Verificar se é segunda ou terça-feira para envio direto
                if today.weekday() not in [0, 1]:
                    logger.warning(f"TENTATIVA DE ENVIO DIRETO FORA DO DIA PERMITIDO - Dia da semana: {today.weekday()}")
                    messages.warning(request, 'Solicitações só podem ser ENVIADAS às segundas e terças-feiras. Salve como rascunho e confirme na segunda/terça da semana posterior.')
                    return render(request, 'create_request.html', {
                        'form': form,
                        'next_week_start': next_week_start,
                        'next_week_end': next_week_end,
                        'is_confirmation_day': is_confirmation_day,
                        'departments': Department.objects.all().order_by('name')
                    })
                    
                scheduled_date = form.cleaned_data.get('scheduled_date')
                if scheduled_date:
                    # Verificar se a data está na próxima semana (segunda a sábado)
                    next_week_start = today + timedelta(days=(7 - today.weekday()))
                    next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado
                    
                    if not (next_week_start <= scheduled_date <= next_week_end):
                        logger.warning(f"DATA FORA DA PROXIMA SEMANA PARA ENVIO DIRETO")
                        form.add_error('scheduled_date', 'Para envio direto, a data deve estar na próxima semana (segunda a sábado).')
                        return render(request, 'create_request.html', {
                            'form': form,
                            'departments': departments,
                            'next_week_start': next_week_start,
                            'next_week_end': next_week_end,
                            'is_confirmation_day': is_confirmation_day
                        })
                    
                    # Verificar se não é domingo
                    if scheduled_date.weekday() == 6:  # 6=domingo
                        logger.warning(f"TENTATIVA DE AGENDAMENTO EM DOMINGO")
                        form.add_error('scheduled_date', 'Não é possível fazer agendamentos aos domingos.')
                        return render(request, 'create_request.html', {
                            'form': form,
                            'departments': departments,
                            'next_week_start': next_week_start,
                            'next_week_end': next_week_end,
                            'is_confirmation_day': is_confirmation_day
                        })
            
            if is_draft:
                # REGRA: Validação para rascunhos - não permitir domingos
                scheduled_date = form.cleaned_data.get('scheduled_date')
                if scheduled_date and scheduled_date.weekday() == 6:  # 6=domingo
                    logger.warning(f"TENTATIVA DE RASCUNHO EM DOMINGO")
                    form.add_error('scheduled_date', 'Domingos não são permitidos para agendamentos. Rascunhos podem ser feitos para qualquer dia exceto domingos.')
                    return render(request, 'create_request.html', {
                        'form': form,
                        'next_week_start': next_week_start,
                        'next_week_end': next_week_end,
                        'is_confirmation_day': is_confirmation_day,
                        'departments': Department.objects.all().order_by('name')
                    })
                
                # Criar rascunho
                draft = DraftScheduleRequest()
                for field in form.cleaned_data:
                    if hasattr(draft, field):
                        setattr(draft, field, form.cleaned_data[field])
                
                # Garantir que os campos obrigatórios estão definidos
                draft.professor = request.user
                draft.laboratory = form.cleaned_data['laboratory']
                
                # Definir horários baseados no turno (se disponível)
                if 'shift' in form.cleaned_data and form.cleaned_data['shift']:
                    draft.shift = form.cleaned_data['shift']
                    draft.set_times_from_shift()
                
                logger.info(f" DADOS DO RASCUNHO:")
                logger.info(f"   Professor: {draft.professor.get_full_name()}")
                logger.info(f"   Laboratório: {draft.laboratory.name if draft.laboratory else 'NULO'}")
                logger.info(f"   Subject: {draft.subject}")
                logger.info(f"   Date: {draft.scheduled_date}")
                logger.info(f"   Turno: {draft.shift}")
                
                # Processar materiais selecionados para rascunho
                selected_materials = request.POST.getlist('selected_materials')
                if selected_materials:
                    materials = Material.objects.filter(id__in=selected_materials)
                    materials_text = ', '.join([mat.name for mat in materials])
                    if draft.materials:
                        draft.materials += f"\n\nMateriais selecionados: {materials_text}"
                    else:
                        draft.materials = f"Materiais selecionados: {materials_text}"
                
                draft.save()
                logger.info(f" RASCUNHO SALVO COM SUCESSO - ID: {draft.pk}")
                if is_confirmation_day:
                    messages.success(request, 'Rascunho salvo com sucesso! Você pode confirmá-lo como solicitação hoje (segunda/terça).')
                else:
                    messages.success(request, 'Rascunho salvo com sucesso! Ele ficará como uma "caixa" e você poderá enviá-lo na segunda ou terça-feira da semana posterior ao agendamento.')
                return redirect('professor_dashboard')
            
            # Continuar com agendamento normal se for segunda/terça
            schedule_request = form.save(commit=False)
            schedule_request.professor = request.user
            
            # Log dos dados antes de salvar
            logger.info(f" DADOS DO AGENDAMENTO:")
            logger.info(f"   Professor: {schedule_request.professor.get_full_name()}")
            logger.info(f"   Laboratório: {schedule_request.laboratory.name}")
            logger.info(f"   Departamento: {schedule_request.laboratory.department}")
            logger.info(f"   Data: {schedule_request.scheduled_date}")
            logger.info(f"   Horário: {schedule_request.start_time} - {schedule_request.end_time}")
            logger.info(f"   Disciplina: {schedule_request.subject}")
            
            # Verificar conflitos
            if schedule_request.is_conflicting():
                logger.warning(f" CONFLITO DE HORÁRIO DETECTADO")
                messages.error(request, 'Já existe um agendamento aprovado para este laboratório neste horário.')
                return render(request, 'create_request.html', {
                    'form': form,
                    'next_week_start': next_week_start,
                    'next_week_end': next_week_end
                })
            
            try:
                # Salvar o agendamento
                logger.info(f" SALVANDO AGENDAMENTO...")
                schedule_request.save()
                invalidate_schedule_caches()  # Invalidar cache
                logger.info(f" AGENDAMENTO SALVO COM SUCESSO - ID: {schedule_request.pk}")
                
                # Processar materiais selecionados
                selected_materials = request.POST.getlist('selected_materials')
                if selected_materials:
                    materials = Material.objects.filter(id__in=selected_materials)
                    # Adicionar materiais selecionados ao campo de texto
                    materials_text = ', '.join([mat.name for mat in materials])
                    if schedule_request.materials:
                        schedule_request.materials += f"\n\nMateriais selecionados: {materials_text}"
                    else:
                        schedule_request.materials = f"Materiais selecionados: {materials_text}"
                    schedule_request.save(update_fields=['materials'])
                    logger.info(f" MATERIAIS SELECIONADOS SALVOS: {len(selected_materials)} itens")
                
                # Verificar se foi realmente salvo
                verificacao = ScheduleRequest.objects.get(pk=schedule_request.pk)
                logger.info(f" VERIFICAÇÃO DB: ID {verificacao.pk} encontrado")
                
                # Notificar laboratoristas (se configurado)
                try:
                    from whatsapp.services import WhatsAppNotificationService
                    WhatsAppNotificationService.notify_schedule_request(schedule_request)
                    logger.info(f" NOTIFICAÇÃO WHATSAPP ENVIADA")
                except Exception as e:
                    logger.warning(f" ERRO AO ENVIAR NOTIFICAÇÃO: {str(e)}")
                
                messages.success(request, 'Solicitação de agendamento enviada com sucesso! Aguarde a aprovação.')
                return redirect('professor_dashboard')
                
            except Exception as e:
                logger.error(f" ERRO AO SALVAR AGENDAMENTO: {str(e)}")
                messages.error(request, f'Erro ao salvar agendamento: {str(e)}')
                return render(request, 'create_request.html', {
                    'form': form,
                    'next_week_start': next_week_start,
                    'next_week_end': next_week_end
                })
        else:
            logger.warning(f" FORMULÁRIO INVÁLIDO: {form.errors}")
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        logger.info(f"EXIBINDO FORMULARIO DE AGENDAMENTO")
        # Por padrão, criar formulário com modo rascunho (permite todo o mês)
        # A validação específica será feita no POST baseado no botão clicado
        form = ScheduleRequestForm(is_draft=True)
    
    # Obter departamentos para o filtro
    from laboratories.models import Department
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'departments': departments,
        'next_week_start': next_week_start,
        'next_week_end': next_week_end,
        'is_confirmation_day': is_confirmation_day
    }
    
    return render(request, 'create_request.html', context)

@login_required
@user_passes_test(is_professor)
def list_draft_schedule_requests(request):
    """
    Lista os rascunhos de agendamento para confirmação (apenas segunda/terça)
    """
    today = timezone.localtime().date()
    
    # Verifica se é segunda ou terça-feira
    if today.weekday() not in [0, 1]:  # 0=segunda, 1=terça
        messages.warning(request, 'Rascunhos só podem ser confirmados às segundas e terças-feiras.')
        return redirect('professor_dashboard')
    
    # NOVA REGRA: Busca rascunhos que podem ser confirmados hoje
    # (rascunhos para agendamentos desta semana - confirmados na segunda/terça)
    
    # Calcular o início da semana atual (segunda-feira)
    current_week_start = today - timezone.timedelta(days=today.weekday())
    current_week_end = current_week_start + timezone.timedelta(days=6)  # Domingo
    
    # Buscar todos os rascunhos do usuário
    all_drafts = DraftScheduleRequest.objects.filter(
        professor=request.user
    ).order_by('scheduled_date')
    
    # Filtrar rascunhos que podem ser confirmados hoje (segunda/terça da semana do agendamento)
    confirmable_drafts = []
    for draft in all_drafts:
        if draft.scheduled_date:
            # Semana do agendamento
            scheduled_week_start = draft.scheduled_date - timezone.timedelta(days=draft.scheduled_date.weekday())
            confirmation_monday = scheduled_week_start
            confirmation_tuesday = scheduled_week_start + timezone.timedelta(days=1)
            
            # Pode confirmar se hoje é segunda ou terça da semana do agendamento
            draft.can_confirm_today = confirmation_monday <= today <= confirmation_tuesday
            if draft.can_confirm_today:
                confirmable_drafts.append(draft)
        else:
            draft.can_confirm_today = False
    
    draft_requests = confirmable_drafts
    
    context = {
        'draft_requests': draft_requests,  # Rascunhos que podem ser confirmados hoje
        'all_drafts': all_drafts,          # Todos os rascunhos com indicação de confirmação
        'can_confirm': True,
        'current_week_start': current_week_start,
        'current_week_end': current_week_end
    }
    
    return render(request, 'draft_requests.html', context)

@login_required
@user_passes_test(is_professor)
def view_draft_schedule_requests(request):
    """
    Visualiza os rascunhos de agendamento (qualquer dia)
    """
    # Busca rascunhos do usuário atual
    draft_requests = DraftScheduleRequest.objects.filter(
        professor=request.user
    ).order_by('scheduled_date')
    
    today = timezone.localtime().date()
    
    # Verificar se existe pelo menos um rascunho que pode ser confirmado hoje
    can_confirm_any = False
    if today.weekday() in [0, 1]:  # Se hoje é segunda ou terça
        for draft in draft_requests:
            # Calcular as datas válidas para este rascunho
            scheduled_date = draft.scheduled_date
            days_to_monday = scheduled_date.weekday()
            schedule_week_monday = scheduled_date - timezone.timedelta(days=days_to_monday)
            previous_week_monday = schedule_week_monday - timezone.timedelta(days=7)
            previous_week_tuesday = previous_week_monday + timezone.timedelta(days=1)
            
            if today in [previous_week_monday, previous_week_tuesday]:
                can_confirm_any = True
                break
    
    context = {
        'draft_requests': draft_requests,
        'can_confirm': can_confirm_any,
        'is_view_only': not can_confirm_any,
        'today': today
    }
    
    return render(request, 'draft_requests.html', context)

@login_required
@user_passes_test(is_professor)
def confirm_draft_schedule_request(request, draft_id):
    """
    Confirma um rascunho de agendamento
    """
    today = timezone.localtime().date()
    
    # REGRA: Verifica se é segunda ou terça-feira
    if today.weekday() not in [0, 1]:  # 0=segunda, 1=terça
        messages.warning(request, 'Rascunhos só podem ser confirmados às segundas e terças-feiras.')
        return redirect('view_draft_schedule_requests')
    
    draft_request = get_object_or_404(DraftScheduleRequest, id=draft_id, professor=request.user)
    
    # Validação adicional: verifica se hoje está na semana anterior ao agendamento
    scheduled_date = draft_request.scheduled_date
    
    # Calcular a segunda-feira da semana do agendamento
    days_to_monday = scheduled_date.weekday()  # 0=segunda, 1=terça, etc.
    schedule_week_monday = scheduled_date - timezone.timedelta(days=days_to_monday)
    
    # Calcular a segunda e terça da semana ANTERIOR ao agendamento
    previous_week_monday = schedule_week_monday - timezone.timedelta(days=7)
    previous_week_tuesday = previous_week_monday + timezone.timedelta(days=1)
    
    # Verificar se hoje é segunda ou terça da semana anterior
    if today not in [previous_week_monday, previous_week_tuesday]:
        # Formatar datas para exibição
        monday_str = previous_week_monday.strftime("%d/%m/%Y")
        tuesday_str = previous_week_tuesday.strftime("%d/%m/%Y")
        schedule_str = scheduled_date.strftime("%d/%m/%Y")
        
        messages.error(request, 
            f'Este rascunho só pode ser confirmado na segunda ({monday_str}) ou terça ({tuesday_str}) '
            f'da semana anterior ao agendamento ({schedule_str})')
        return redirect('view_draft_schedule_requests')
    
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
        class_semester=draft_request.class_semester,
        materials=draft_request.materials,
        guide_file=draft_request.guide_file,
    )
    
    invalidate_schedule_caches()  # Invalidar cache
    
    # Verifica conflitos de horário
    if schedule_request.is_conflicting():
        # Se houver conflito, deleta a solicitação e mantém o rascunho
        schedule_request.delete()
        messages.error(request, 'Já existe um agendamento aprovado para este laboratório neste horário.')
        return redirect('view_draft_schedule_requests')
    
    
    # Deleta o rascunho após confirmação
    draft_request.delete()
    
    messages.success(request, f'Solicitação de agendamento "{schedule_request.subject}" enviada com sucesso! Aguarde a aprovação do técnico.')
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
    return redirect('view_draft_schedule_requests')

@login_required
def schedule_request_detail(request, pk):
    """Exibe detalhes de uma solicitação de agendamento com comentários"""
    schedule_request = get_object_or_404(
        ScheduleRequest.objects.select_related(
            'professor', 'laboratory', 'reviewed_by'
        ).prefetch_related(
            'laboratory__departments', 'comments__author'
        ), 
        pk=pk
    )
    
    # Verifica se o usuário tem permissão para visualizar
    if request.user.user_type == 'professor' and schedule_request.professor != request.user:
        messages.error(request, 'Você não tem permissão para visualizar esta solicitação.')
        return redirect('professor_dashboard')
    
    # Processar adição de comentário
    if request.method == 'POST' and 'add_comment' in request.POST:
        comment_text = request.POST.get('comment_message', '').strip()
        if comment_text:
            comment = ScheduleRequestComment.objects.create(
                schedule_request=schedule_request,
                author=request.user,
                message=comment_text
            )
            
            # Enviar notificação WhatsApp baseada no tipo de usuário
            try:
                if request.user.user_type == 'professor':
                    # Professor enviou mensagem -> notificar técnicos
                    WhatsAppNotificationService.notify_professor_message(comment)
                elif request.user.user_type == 'technician':
                    # Técnico enviou mensagem -> notificar professor
                    WhatsAppNotificationService.notify_technician_message(comment)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Erro ao enviar notificação WhatsApp para mensagem: {str(e)}")
            
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('schedule_request_detail', pk=pk)
        else:
            messages.error(request, 'O comentário não pode estar vazio.')
    
    # Obter todos os comentários
    comments = schedule_request.comments.all()
    
    # Marcar comentários como lidos para o usuário atual
    unread_comments = comments.filter(is_read=False).exclude(author=request.user)
    unread_comments.update(is_read=True)
    
    # Informações sobre o prazo
    schedule_request.approval_deadline = schedule_request.get_approval_deadline()
    schedule_request.days_remaining = schedule_request.days_until_approval_deadline()
    schedule_request.is_overdue = schedule_request.is_approval_overdue()
    
    context = {
        'schedule_request': schedule_request,
        'comments': comments,
        'can_comment': True,  # Tanto professores quanto técnicos podem comentar
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
    
    # Verifica se é uma segunda ou terça-feira
    today = timezone.localtime().date()
    if today.weekday() not in [0, 1] or settings.ALLOW_SCHEDULING_ANY_DAY:  # 0=segunda, 1=terça
        messages.warning(request, 'Agendamentos só podem ser modificados às segundas e terças-feiras.')
        return redirect('schedule_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES, instance=schedule_request, is_draft=False)
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
        form = ScheduleRequestForm(instance=schedule_request, is_draft=False)
    
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
        return redirect('pending_requests')
    
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
        return redirect('pending_requests')
    
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
        return redirect('pending_requests')
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        # Rejeita a solicitação
        schedule_request.reject(request.user, rejection_reason)

        # Adicionar: Enviar notificação WhatsApp
        WhatsAppNotificationService.notify_schedule_rejection(schedule_request)
        
        messages.success(request, f'Solicitação de agendamento de {schedule_request.professor.get_full_name()} rejeitada com sucesso.')
        return redirect('pending_requests')
    
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
    import logging
    logger = logging.getLogger(__name__)
    
    draft_request = get_object_or_404(DraftScheduleRequest, id=draft_id, professor=request.user)
    logger.info(f" EDITANDO RASCUNHO ID: {draft_id}")
    logger.info(f"   Laboratory: {draft_request.laboratory.name if draft_request.laboratory else 'None'}")
    logger.info(f"   Subject: {draft_request.subject}")
    logger.info(f"   Shift: {draft_request.shift}")
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES, instance=draft_request, is_draft=True)
        
        # Atualizar queryset de materiais baseado no laboratório selecionado
        if 'laboratory' in request.POST and request.POST['laboratory']:
            try:
                lab_id = int(request.POST['laboratory'])
                from inventory.models import Material
                form.fields['selected_materials'].queryset = Material.objects.filter(laboratory_id=lab_id)
                logger.info(f" QUERYSET DE MATERIAIS ATUALIZADO PARA LAB {lab_id}")
            except (ValueError, TypeError):
                logger.warning(f" ERRO AO PROCESSAR LAB ID: {request.POST.get('laboratory')}")
        
        if form.is_valid():
            # CORREÇÃO: Não usar form.save() pois o form é de ScheduleRequest, não DraftScheduleRequest
            # Copiar dados manualmente para o rascunho existente
            draft_request.laboratory = form.cleaned_data['laboratory']
            draft_request.subject = form.cleaned_data['subject']
            draft_request.description = form.cleaned_data['description']
            draft_request.scheduled_date = form.cleaned_data['scheduled_date']
            draft_request.number_of_students = form.cleaned_data['number_of_students']
            draft_request.class_semester = form.cleaned_data['class_semester']
            
            # Processar turno para definir horários
            if 'shift' in form.cleaned_data and form.cleaned_data['shift']:
                draft_request.shift = form.cleaned_data['shift']
                draft_request.set_times_from_shift()
            
            # Processar arquivo de roteiro
            if form.cleaned_data.get('guide_file'):
                draft_request.guide_file = form.cleaned_data['guide_file']
            
            # Processar materiais selecionados
            selected_materials = request.POST.getlist('selected_materials')
            materials_text_from_form = form.cleaned_data.get('materials', '')
            
            if selected_materials:
                materials = Material.objects.filter(id__in=selected_materials)
                materials_list = ', '.join([mat.name for mat in materials])
                
                # Combinar materiais do texto livre com selecionados
                if materials_text_from_form:
                    draft_request.materials = f"{materials_text_from_form}\n\nMateriais selecionados: {materials_list}"
                else:
                    draft_request.materials = f"Materiais selecionados: {materials_list}"
            else:
                draft_request.materials = materials_text_from_form
            
            draft_request.save()
            logger.info(f" RASCUNHO ATUALIZADO COM SUCESSO - ID: {draft_request.pk}")
            messages.success(request, 'Rascunho de agendamento atualizado com sucesso!')
            return redirect('view_draft_schedule_requests')
    else:
        # Não usar instance= porque são modelos diferentes (DraftScheduleRequest vs ScheduleRequest)
        # Em vez disso, usar initial para preencher os campos
        initial_data = {
            'laboratory': draft_request.laboratory.id if draft_request.laboratory else None,
            'subject': draft_request.subject,
            'description': draft_request.description,
            'scheduled_date': draft_request.scheduled_date,
            'number_of_students': draft_request.number_of_students,
            'class_semester': draft_request.class_semester,
            'materials': draft_request.materials,
            'shift': getattr(draft_request, 'shift', 'evening'),
            'guide_file': draft_request.guide_file if hasattr(draft_request, 'guide_file') else None,
        }
        
        logger.info(f"📅 INITIAL DATA PARA EDIÇÃO:")
        logger.info(f"   scheduled_date: {initial_data['scheduled_date']} (tipo: {type(initial_data['scheduled_date'])})")
        logger.info(f"   subject: {initial_data['subject']}")
        logger.info(f"   shift: {initial_data['shift']}")
        
        form = ScheduleRequestForm(initial=initial_data, is_draft=True)
        
        # Garantir que o campo de data tenha o valor correto no widget
        if draft_request.scheduled_date:
            form.fields['scheduled_date'].widget.attrs['value'] = draft_request.scheduled_date.strftime('%Y-%m-%d')
            logger.info(f"📅 FORÇANDO VALOR DE DATA NO WIDGET: {draft_request.scheduled_date.strftime('%Y-%m-%d')}")
        
        logger.info(f" RASCUNHO CARREGADO PARA EDIÇÃO: {draft_request.subject or 'Sem título'}")
        
        # Configurar queryset de materiais para o laboratório do rascunho
        if draft_request.laboratory:
            logger.info(f"🔧 CONFIGURANDO MATERIAIS PARA LAB: {draft_request.laboratory.name}")
            from inventory.models import Material
            form.fields['selected_materials'].queryset = Material.objects.filter(
                laboratory=draft_request.laboratory
            )
            
            # Extrair materiais já selecionados do campo de texto
            selected_material_ids = []
            if draft_request.materials:
                # Procurar por linha que contém "Materiais selecionados:"
                for line in draft_request.materials.split('\n'):
                    if 'Materiais selecionados:' in line:
                        # Extrair nomes dos materiais
                        materials_text = line.replace('Materiais selecionados:', '').strip()
                        material_names = [name.strip() for name in materials_text.split(',') if name.strip()]
                        
                        # Encontrar IDs dos materiais pelos nomes
                        for name in material_names:
                            try:
                                material = Material.objects.get(
                                    name__icontains=name,
                                    laboratory=draft_request.laboratory
                                )
                                selected_material_ids.append(material.id)
                                logger.info(f" MATERIAL ENCONTRADO: {material.name} (ID: {material.id})")
                            except Material.DoesNotExist:
                                logger.warning(f" MATERIAL NÃO ENCONTRADO: {name}")
                            except Material.MultipleObjectsReturned:
                                # Se há múltiplos, pegar o primeiro
                                material = Material.objects.filter(
                                    name__icontains=name,
                                    laboratory=draft_request.laboratory
                                ).first()
                                if material:
                                    selected_material_ids.append(material.id)
                                    logger.info(f" MATERIAL ENCONTRADO (MÚLTIPLOS): {material.name} (ID: {material.id})")
            
            # Definir materiais selecionados no formulário
            if selected_material_ids:
                form.initial['selected_materials'] = selected_material_ids
                logger.info(f" MATERIAIS PRÉ-SELECIONADOS: {len(selected_material_ids)} itens")
        
        # Configurar turno baseado nos horários ou campo shift
        if hasattr(draft_request, 'shift') and draft_request.shift:
            form.initial['shift'] = draft_request.shift
            logger.info(f"🕐 TURNO PRÉ-SELECIONADO: {draft_request.shift}")
        elif draft_request.start_time:
            # Determinar turno baseado no horário de início
            start_hour = draft_request.start_time.hour
            if 7 <= start_hour < 12:
                form.initial['shift'] = 'morning'
            elif 19 <= start_hour < 23:
                form.initial['shift'] = 'evening'
            logger.info(f"🕐 TURNO DETERMINADO PELO HORÁRIO: {form.initial.get('shift', 'indefinido')}")
        
        logger.info(f" DADOS INICIAIS DO FORMULÁRIO: {form.initial}")
    
    # Obter departamentos para filtro
    from laboratories.models import Department
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'departments': departments,
        'title': 'Editar Rascunho de Agendamento',
        'is_edit': True,
        'draft_id': draft_id,
        'draft_request': draft_request,
    }
    
    return render(request, 'create_request.html', context)


def calendar_data_api(request):
    """API para dados do calendário via AJAX"""
    # Obter parâmetros da requisição
    week_offset = int(request.GET.get('week_offset', 0))
    month_offset = int(request.GET.get('month_offset', 0))
    filter_labs = request.GET.getlist('labs[]', [])
    filter_status = request.GET.get('status', 'all')
    
    # Determinar período de datas
    today = timezone.localtime().date()
    
    # Se for navegação mensal
    if month_offset != 0:
        target_date = today.replace(day=1) + timedelta(days=32 * month_offset)
        start_date = target_date.replace(day=1) - timedelta(days=31)
        end_date = target_date.replace(day=1) + timedelta(days=62)
    else:
        start_date = today - timedelta(days=today.weekday())
        start_date = start_date + timedelta(weeks=week_offset)
        end_date = start_date + timedelta(days=27)
    
    # Construir filtro para laboratórios
    lab_filter = {}
    if filter_labs and 'all' not in filter_labs:
        lab_filter['laboratory__id__in'] = filter_labs
    
    # Buscar todos os agendamentos
    schedule_requests = ScheduleRequest.objects.filter(
        scheduled_date__range=[start_date, end_date],
        **lab_filter
    ).select_related('professor', 'laboratory')
    
    # Se o usuário for professor, mostrar apenas seus agendamentos
    if request.user.user_type == 'professor':
        schedule_requests = schedule_requests.filter(professor=request.user)
    
    # Converter para formato JSON - CAMPOS CORRETOS
    events = []
    for schedule in schedule_requests:
        # Aplicar filtro de status no frontend se necessário
        if filter_status != 'all' and schedule.status != filter_status:
            continue
            
        events.append({
            'id': schedule.id,
            'date': schedule.scheduled_date.strftime('%Y-%m-%d'),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'laboratory_id': schedule.laboratory.id,
            'laboratory_name': schedule.laboratory.name,
            'professor_name': schedule.professor.get_full_name(),
            'subject': schedule.subject or 'Não informado',
            'status': schedule.status,
            'description': schedule.description or '',
            'number_of_students': schedule.number_of_students or 0,  # CAMPO CORRETO
            'is_exception': schedule.is_exception,  # CAMPO PARA AGENDAMENTOS DE EXCEÇÃO
        })
    
    # Organizar dados por semanas e dias
    calendar_data = []
    
    current_date = start_date
    for week in range(4):
        week_data = []
        
        for day in range(7):
            day_schedules = []
            
            # Filtrar agendamentos para este dia
            day_requests = [e for e in events if e['date'] == current_date.strftime('%Y-%m-%d')]
            
            for request in day_requests:
                day_schedules.append({
                    'id': request['id'],
                    'start_time': request['start_time'],
                    'end_time': request['end_time'],
                    'laboratory_name': request['laboratory_name'],
                    'professor_name': request['professor_name'],
                    'subject': request['subject'],
                    'status': request['status'],
                })
            
            week_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day_name': current_date.strftime('%a'),
                'is_today': current_date == today,
                'schedules': day_schedules
            })
            
            current_date += timedelta(days=1)
        
        calendar_data.append(week_data)
    
    return JsonResponse({
        'success': True,
        'events': events,
        'calendar_data': calendar_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
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


@login_required
def get_laboratory_materials(request, laboratory_id):
    """API para buscar materiais de um laboratório"""
    try:
        laboratory = get_object_or_404(Laboratory, id=laboratory_id, is_active=True)
        materials = Material.objects.filter(laboratory=laboratory).select_related('category')
        
        materials_data = []
        for material in materials:
            materials_data.append({
                'id': material.id,
                'name': material.name,
                'description': material.description,
                'quantity': material.quantity,
                'minimum_stock': material.minimum_stock,
                'is_low_stock': material.is_low_stock,
                'category': material.category.name,
                'category_type': material.category.material_type,
            })
        
        return JsonResponse({
            'materials': materials_data,
            'laboratory_name': laboratory.name,
            'total_materials': len(materials_data)
        })
        
    except Laboratory.DoesNotExist:
        return JsonResponse({'error': 'Laboratório não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_technician)
def pending_requests_list(request):
    """Lista todas as solicitações pendentes para técnicos - OTIMIZADA"""
    
    # Processar aprovação/rejeição via POST
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        action = request.POST.get('action')
        
        if schedule_id and action:
            try:
                schedule_request = ScheduleRequest.objects.select_related('professor', 'laboratory').get(
                    id=schedule_id, status='pending'
                )
                
                if action == 'approve':
                    if schedule_request.is_conflicting():
                        messages.error(request, 'Existe conflito de horário com outro agendamento já aprovado.')
                    else:
                        schedule_request.approve(request.user)
                        WhatsAppNotificationService.notify_schedule_approval(schedule_request)
                        invalidate_schedule_caches()  # Invalidar cache
                        messages.success(request, f'Solicitação de {schedule_request.professor.get_full_name()} aprovada com sucesso.')
                
                elif action == 'reject':
                    rejection_reason = request.POST.get('rejection_reason', '')
                    schedule_request.reject(request.user, rejection_reason)
                    WhatsAppNotificationService.notify_schedule_rejection(schedule_request)
                    invalidate_schedule_caches()  # Invalidar cache
                    messages.success(request, f'Solicitação de {schedule_request.professor.get_full_name()} rejeitada.')
                    
            except ScheduleRequest.DoesNotExist:
                messages.error(request, 'Solicitação não encontrada ou já foi processada.')
        
        return redirect('pending_requests')
    
    # Query otimizada com CACHE - limitar a 50 mais recentes e usar índices
    cache_key = 'pending_requests_list'
    pending_requests = cache.get(cache_key)
    
    if pending_requests is None:
        pending_requests = list(ScheduleRequest.objects.filter(
            status='pending'
        ).select_related('professor', 'laboratory').only(
            'id', 'request_date', 'scheduled_date', 'start_time', 'end_time',
            'subject', 'number_of_students', 'description', 'materials', 'guide_file',
            'professor__first_name', 'professor__last_name', 'professor__email',
            'laboratory__name'
        ).order_by('-request_date')[:50])  # Limitar a 50 mais recentes
        
        # Cache por 2 minutos
        cache.set(cache_key, pending_requests, 120)
    
    # Adicionar informações sobre prazo e comentários para cada solicitação
    today = timezone.localtime().date()
    for schedule_req in pending_requests:
        schedule_req.approval_deadline = schedule_req.get_approval_deadline()
        schedule_req.days_remaining = schedule_req.days_until_approval_deadline()
        schedule_req.is_overdue = schedule_req.is_approval_overdue()
        schedule_req.is_urgent = schedule_req.days_remaining is not None and schedule_req.days_remaining <= 1
        
        # Informações sobre comentários
        comments_count = ScheduleRequestComment.objects.filter(schedule_request=schedule_req).count()
        unread_count = ScheduleRequestComment.objects.filter(
            schedule_request=schedule_req,
            is_read=False
        ).exclude(author=request.user).count()
        
        schedule_req.comments_count = comments_count
        schedule_req.unread_comments = unread_count
        schedule_req.has_conversation = comments_count > 0
    
    context = {
        'pending_requests': pending_requests,
        'title': 'Solicitações Pendentes',
        'total_count': ScheduleRequest.objects.filter(status='pending').count(),
        'today': today
    }
    
    return render(request, 'pending_requests.html', context)


@login_required
def add_comment_to_request(request, pk):
    """API endpoint para adicionar comentário via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    # Verificar permissões
    if (request.user.user_type == 'professor' and schedule_request.professor != request.user) and \
       request.user.user_type != 'technician':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    comment_text = request.POST.get('message', '').strip()
    if not comment_text:
        return JsonResponse({'error': 'Mensagem não pode estar vazia'}, status=400)
    
    # Criar comentário
    comment = ScheduleRequestComment.objects.create(
        schedule_request=schedule_request,
        author=request.user,
        message=comment_text
    )
    
    # Enviar notificação WhatsApp baseada no tipo de usuário
    try:
        if request.user.user_type == 'professor':
            # Professor enviou mensagem -> notificar técnicos
            WhatsAppNotificationService.notify_professor_message(comment)
        elif request.user.user_type == 'technician':
            # Técnico enviou mensagem -> notificar professor
            WhatsAppNotificationService.notify_technician_message(comment)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Erro ao enviar notificação WhatsApp para mensagem: {str(e)}")
    
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'author_name': comment.author.get_full_name(),
            'author_type': comment.author.user_type,
            'message': comment.message,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            'is_own': comment.author == request.user
        }
    })


@login_required  
def get_request_comments(request, pk):
    """API endpoint para obter comentários via AJAX"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    # Verificar permissões
    if (request.user.user_type == 'professor' and schedule_request.professor != request.user) and \
       request.user.user_type != 'technician':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    comments = schedule_request.comments.select_related('author').all()
    
    # Marcar como lidas
    unread_comments = comments.filter(is_read=False).exclude(author=request.user)
    unread_comments.update(is_read=True)
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'author_name': comment.author.get_full_name(),
            'author_type': comment.author.user_type,
            'message': comment.message,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            'is_own': comment.author == request.user
        })
    
    return JsonResponse({'comments': comments_data})


@login_required
@user_passes_test(is_professor)
def my_schedule_requests(request):
    """Lista todas as solicitações do professor atual"""
    professor = request.user
    
    # Obter filtro de status
    status_filter = request.GET.get('status', 'all')
    
    # Query base
    requests_query = ScheduleRequest.objects.filter(professor=professor)
    
    # Aplicar filtro de status
    if status_filter and status_filter != 'all':
        requests_query = requests_query.filter(status=status_filter)
    
    # Buscar solicitações com relacionamentos
    schedule_requests = requests_query.select_related(
        'laboratory', 'reviewed_by'
    ).prefetch_related(
        'comments__author'
    ).order_by('-request_date')
    
    # Adicionar informações extras para cada solicitação
    for schedule_req in schedule_requests:
        # Informações sobre comentários
        comments_count = schedule_req.comments.count()
        unread_count = schedule_req.comments.filter(
            is_read=False
        ).exclude(author=request.user).count()
        
        schedule_req.comments_count = comments_count
        schedule_req.unread_comments = unread_count
        schedule_req.has_conversation = comments_count > 0
        
        # Informações sobre prazo (se pendente)
        if schedule_req.status == 'pending':
            schedule_req.approval_deadline = schedule_req.get_approval_deadline()
            schedule_req.days_remaining = schedule_req.days_until_approval_deadline()
            schedule_req.is_overdue = schedule_req.is_approval_overdue()
    
    # Contar por status
    status_counts = {
        'all': ScheduleRequest.objects.filter(professor=professor).count(),
        'pending': ScheduleRequest.objects.filter(professor=professor, status='pending').count(),
        'approved': ScheduleRequest.objects.filter(professor=professor, status='approved').count(),
        'rejected': ScheduleRequest.objects.filter(professor=professor, status='rejected').count(),
    }
    
    context = {
        'schedule_requests': schedule_requests,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'title': 'Minhas Solicitações',
    }
    
    return render(request, 'my_requests.html', context)


@login_required
def mark_all_notifications_read(request):
    """Marcar todas as notificações como lidas"""
    if request.method == 'POST':
        # Marcar mensagens como lidas baseado no tipo de usuário
        if request.user.user_type == 'professor':
            # Marcar mensagens de técnicos como lidas
            ScheduleRequestComment.objects.filter(
                schedule_request__professor=request.user,
                is_read=False
            ).exclude(author=request.user).update(is_read=True)
        
        elif request.user.user_type == 'technician':
            # Marcar mensagens de professores como lidas
            ScheduleRequestComment.objects.filter(
                schedule_request__status='pending',
                is_read=False
            ).exclude(author=request.user).update(is_read=True)
        
        return JsonResponse({'success': True})


@login_required
def all_notifications(request):
    """Página para mostrar todas as notificações do usuário"""
    notifications = []
    
    if request.user.user_type == 'technician':
        # Unread messages from professors
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__status='pending',
            is_read=False
        ).exclude(author=request.user).select_related('author', 'schedule_request').order_by('-created_at')
        
        # Create notifications for unread messages
        for message in unread_messages:
            notifications.append({
                'title': f'Mensagem de {message.author.get_full_name()}',
                'message': message.message,
                'timestamp': message.created_at,
                'type': 'message',
                'url': f'/scheduling/request/{message.schedule_request.id}/',
                'icon': 'bi bi-chat-dots',
                'is_read': message.is_read
            })
        
        # Pending appointment requests
        pending_requests = ScheduleRequest.objects.filter(status='pending').order_by('-request_date')
        for request_obj in pending_requests:
            notifications.append({
                'title': 'Solicitação Pendente',
                'message': f'Agendamento para {request_obj.laboratory.name} por {request_obj.professor.get_full_name()}',
                'timestamp': request_obj.request_date,
                'type': 'pending_request',
                'url': f'/scheduling/request/{request_obj.id}/',
                'icon': 'bi bi-hourglass-split',
                'is_read': True  # These don't have read status
            })
        
        # Pending user approvals
        pending_users = User.objects.filter(is_approved=False).order_by('-date_joined')
        for user_obj in pending_users:
            notifications.append({
                'title': 'Usuário Aguardando Aprovação',
                'message': f'{user_obj.get_full_name()} ({user_obj.email}) aguarda aprovação',
                'timestamp': user_obj.date_joined,
                'type': 'pending_user',
                'url': '/accounts/pending-users/',
                'icon': 'bi bi-person-plus',
                'is_read': True  # These don't have read status
            })
    
    elif request.user.user_type == 'professor':
        # Unread messages from technicians
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__professor=request.user,
            is_read=False
        ).exclude(author=request.user).select_related('author', 'schedule_request').order_by('-created_at')
        
        # Create notifications for unread messages
        for message in unread_messages:
            notifications.append({
                'title': f'Mensagem do Técnico',
                'message': message.message,
                'timestamp': message.created_at,
                'type': 'message',
                'url': f'/scheduling/request/{message.schedule_request.id}/',
                'icon': 'bi bi-chat-dots',
                'is_read': message.is_read
            })
        
        # Recent status updates (approved/rejected)
        recent_reviews = ScheduleRequest.objects.filter(
            professor=request.user,
            status__in=['approved', 'rejected'],
            review_date__isnull=False
        ).order_by('-review_date')
        
        for review in recent_reviews:
            status_text = 'aprovada' if review.status == 'approved' else 'rejeitada'
            notifications.append({
                'title': f'Solicitação {status_text}',
                'message': f'Sua solicitação para {review.laboratory.name} foi {status_text}',
                'timestamp': review.review_date,
                'type': 'status_update',
                'url': f'/scheduling/request/{review.id}/',
                'icon': 'bi bi-check-circle' if review.status == 'approved' else 'bi bi-x-circle',
                'is_read': True  # Status updates are considered read when viewed
            })
    
    # Sort notifications by timestamp (most recent first)
    notifications.sort(key=lambda x: x['timestamp'] or timezone.now(), reverse=True)
    
    # Pagination
    paginator = Paginator(notifications, 20)  # Show 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'scheduling/all_notifications.html', {
        'page_obj': page_obj,
        'notifications': page_obj.object_list
    })


@login_required
@user_passes_test(is_technician)
def technician_edit_schedule(request, pk):
    """Permite ao técnico editar um agendamento aprovado"""
    schedule_request = get_object_or_404(ScheduleRequest, pk=pk)
    
    # Verificar se o agendamento está pendente
    if schedule_request.status != 'pending':
        messages.error(request, 'Apenas agendamentos pendentes podem ser editados.')
        return redirect('pending_requests')
    
    if request.method == 'POST':
        form = ScheduleRequestForm(request.POST, request.FILES, instance=schedule_request)
        form.is_draft = False  # Não é rascunho
        
        if form.is_valid():
            # Verificar se houve mudanças
            original_data = {
                'laboratory': schedule_request.laboratory,
                'scheduled_date': schedule_request.scheduled_date,
                'start_time': schedule_request.start_time,
                'end_time': schedule_request.end_time,
                'subject': schedule_request.subject,
                'description': schedule_request.description,
                'number_of_students': schedule_request.number_of_students,
            }
            
            # Salvar o agendamento editado
            updated_schedule = form.save(commit=False)
            updated_schedule.reviewed_by = request.user
            updated_schedule.review_date = timezone.now()
            updated_schedule.save()
            
            # Verificar quais campos foram alterados
            changes = []
            if original_data['laboratory'] != updated_schedule.laboratory:
                changes.append(f"Laboratório alterado de '{original_data['laboratory'].name}' para '{updated_schedule.laboratory.name}'")
            if original_data['scheduled_date'] != updated_schedule.scheduled_date:
                changes.append(f"Data alterada de {original_data['scheduled_date'].strftime('%d/%m/%Y')} para {updated_schedule.scheduled_date.strftime('%d/%m/%Y')}")
            if original_data['start_time'] != updated_schedule.start_time:
                changes.append(f"Horário de início alterado de {original_data['start_time'].strftime('%H:%M')} para {updated_schedule.start_time.strftime('%H:%M')}")
            if original_data['end_time'] != updated_schedule.end_time:
                changes.append(f"Horário de término alterado de {original_data['end_time'].strftime('%H:%M')} para {updated_schedule.end_time.strftime('%H:%M')}")
            if original_data['number_of_students'] != updated_schedule.number_of_students:
                changes.append(f"Número de alunos alterado de {original_data['number_of_students']} para {updated_schedule.number_of_students}")
            
            # Criar mensagem automática para o professor se houve mudanças
            if changes:
                change_message = "O técnico fez as seguintes alterações no seu agendamento:\n\n" + "\n".join(f"• {change}" for change in changes)
                
                ScheduleRequestComment.objects.create(
                    schedule_request=updated_schedule,
                    author=request.user,
                    message=change_message,
                    is_read=False
                )
                
                messages.success(request, f'Agendamento editado com sucesso. O professor foi notificado automaticamente sobre as alterações.')
            else:
                messages.info(request, 'Nenhuma alteração foi detectada.')
            
            return redirect('pending_requests')
    else:
        form = ScheduleRequestForm(instance=schedule_request)
        form.is_draft = False
        
        # Configurar materiais do laboratório
        if schedule_request.laboratory:
            form.fields['selected_materials'].queryset = Material.objects.filter(
                laboratory=schedule_request.laboratory
            )
    
    context = {
        'form': form,
        'schedule_request': schedule_request,
        'is_edit': True,
        'is_technician_edit': True,
        'title': f'Editar Agendamento - {schedule_request.professor.get_full_name()}',
        'departments': Department.objects.filter(is_active=True) if Department.objects.exists() else [],
    }
    
    return render(request, 'scheduling/technician_edit_schedule.html', context)


@login_required
@user_passes_test(is_technician)
def create_exception_schedule(request):
    """
    View para técnicos criarem agendamentos de exceção para professores
    em dias/horários não liberados normalmente
    """
    if request.method == 'POST':
        form = ExceptionScheduleRequestForm(request.POST, request.FILES, technician=request.user)
        if form.is_valid():
            try:
                # Salvar o agendamento de exceção
                schedule_request = form.save(commit=False)
                
                # Definir horários baseados no período selecionado
                period = form.cleaned_data.get('period')
                if period == 'matutino':
                    schedule_request.start_time = time(7, 0)  # 7:00
                    schedule_request.end_time = time(12, 0)   # 12:00
                elif period == 'noturno':
                    schedule_request.start_time = time(19, 0)  # 19:00
                    schedule_request.end_time = time(23, 0)    # 23:00
                
                # Marcar como agendamento de exceção (caso o form não tenha feito)
                schedule_request.is_exception = True
                schedule_request.created_by_technician = request.user
                schedule_request.status = 'approved'  # Exceções são automaticamente aprovadas
                schedule_request.reviewed_by = request.user
                schedule_request.review_date = timezone.now()
                
                schedule_request.save()
                
                # Enviar notificação WhatsApp para o professor
                try:
                    WhatsAppNotificationService.notify_exception_schedule(schedule_request)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Erro ao enviar notificação WhatsApp para agendamento de exceção: {str(e)}")
                
                messages.success(
                    request, 
                    f'Agendamento de exceção criado com sucesso para {schedule_request.professor.get_full_name()}! '
                    f'O professor foi notificado sobre este agendamento excepcional.'
                )
                return redirect('pending_requests')
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao criar agendamento de exceção: {str(e)}")
                messages.error(request, 'Erro ao criar agendamento de exceção. Tente novamente.')
    else:
        form = ExceptionScheduleRequestForm(technician=request.user)
    
    # Obter departamentos para filtro
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'departments': departments,
        'title': 'Criar Agendamento de Exceção',
        'is_exception': True,
    }
    
    return render(request, 'scheduling/create_exception_schedule.html', context)


@login_required
@user_passes_test(is_professor)
def storage_materials_api(request):
    """API para buscar materiais disponíveis nos laboratórios de estoque"""
    
    # Buscar laboratórios de estoque ativos
    storage_labs = Laboratory.objects.filter(is_active=True, is_storage=True)
    
    # Buscar materiais nesses laboratórios
    materials = Material.objects.filter(
        laboratory__in=storage_labs,
        quantity__gt=0  # Apenas materiais com estoque disponível
    ).select_related('category', 'laboratory').order_by('laboratory__name', 'name')
    
    # Organizar por laboratório
    materials_by_lab = {}
    for material in materials:
        lab_name = material.laboratory.name
        if lab_name not in materials_by_lab:
            materials_by_lab[lab_name] = []
        
        materials_by_lab[lab_name].append({
            'id': material.id,
            'name': material.name,
            'category': material.category.name if material.category else 'Sem categoria',
            'quantity': material.quantity,
            'description': material.description or '',
            'expiration_date': material.expiration_date.strftime('%d/%m/%Y') if material.expiration_date else None,
            'is_near_expiration': material.is_near_expiration if hasattr(material, 'is_near_expiration') else False,
            'is_expired': material.is_expired if hasattr(material, 'is_expired') else False,
        })
    
    return JsonResponse({
        'success': True,
        'storage_labs_count': storage_labs.count(),
        'materials_by_lab': materials_by_lab
    })


@login_required
def serve_guide_file(request, file_path):
    """
    Serve arquivos de media de forma segura com autenticação
    """
    # Construir caminho completo do arquivo
    full_path = os.path.join(settings.MEDIA_ROOT, 'lab_guides', file_path)
    
    # Verificar se arquivo existe
    if not os.path.exists(full_path):
        raise Http404("Arquivo não encontrado")
    
    # Verificar se é um arquivo válido (não um diretório)
    if not os.path.isfile(full_path):
        raise Http404("Caminho inválido")
    
    # Verificar se o usuário tem permissão para acessar o arquivo
    # Buscar o agendamento que contém este arquivo
    schedule_request = get_object_or_404(
        ScheduleRequest, 
        guide_file__icontains=file_path
    )
    
    # Verificar permissões
    if request.user.user_type == 'professor':
        # Professor pode acessar seus próprios arquivos
        if schedule_request.professor != request.user:
            raise Http404("Sem permissão para acessar este arquivo")
    elif request.user.user_type == 'technician':
        # Técnico pode acessar todos os arquivos
        pass
    else:
        # Outros tipos de usuário não podem acessar
        raise Http404("Sem permissão para acessar este arquivo")
    
    # Determinar tipo MIME
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Verificar se deve ser download ou visualização
    is_download = request.GET.get('download', '0') == '1'
    
    # Retornar arquivo
    return FileResponse(
        open(full_path, 'rb'),
        content_type=content_type,
        as_attachment=is_download,  # True para download, False para visualizar
        filename=os.path.basename(full_path)
    )
