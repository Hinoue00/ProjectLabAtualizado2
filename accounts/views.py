# accounts/views.py

from datetime import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from scheduling.forms import PasswordChangeForm, ProfileUpdateForm
from scheduling.models import ScheduleRequest
from .forms import UserRegistrationForm, UserApprovalForm
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from whatsapp.services import WhatsAppNotificationService

def login_register_view(request):
    """
    View combinada para login e registro
    """
    # Se o usuário já está autenticado, redirecionar para dashboard
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    
    # Processar o formulário de login
    if request.method == 'POST' and 'password' in request.POST and 'username' in request.POST:
        email = request.POST['username']  # O campo ainda é chamado 'username' no formulário
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard_redirect')
            return redirect(next_url)
        else:
            messages.error(request, 'Email ou senha inválidos.')
    
    # Processar o formulário de registro
    elif request.method == 'POST' and 'first_name' in request.POST:
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # Pode fazer login mas com acesso limitado até aprovação
            user.save()
            
            # Enviar notificação por email para os laboratoristas sobre novo registro
            technicians = User.objects.filter(user_type='technician', is_approved=True)
            technician_emails = [tech.email for tech in technicians]
            
            if technician_emails:
                subject = 'Novo Usuário Registrado'
                message = f'Um novo usuário ({user.get_full_name()}) se registrou e está aguardando aprovação.'
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, technician_emails)
            
            # Enviar notificação por WhatsApp
            WhatsAppNotificationService.notify_user_registration(user)

            # Fazer login automático, redirecionando para a página de aguardando aprovação
            login(request, user)
            return redirect('pending_user')
        else:
            # Retornar para a página com o formulário de registro ativo
            # e exibir mensagens de erro
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return render(request, 'login_register.html')

def pending_user(request):
    """
    Página exibida enquanto o usuário aguarda aprovação
    """
    if request.user.is_approved:
        return redirect('dashboard_redirect')
    
    return render(request, 'pending_user.html')

@login_required
def dashboard_redirect(request):
    """
    Redireciona usuários para o dashboard apropriado com base no tipo e status de aprovação
    """
    if not request.user.is_approved:
        return redirect('pending_user')
    
    if request.user.user_type == 'technician':
        return redirect('technician_dashboard')
    else:
        return redirect('professor_dashboard')

def is_technician(user):
    return user.is_authenticated and (user.is_superuser or (user.user_type == 'technician' and user.is_approved))

def is_professor(user):
    return user.is_authenticated and user.user_type == 'professor' and user.is_approved

@login_required
@user_passes_test(is_technician)
def pending_approvals(request):
    pending_users = User.objects.filter(is_approved=False)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_id and action:
            user = User.objects.get(id=user_id)
            
            if action == 'approve':
                user.is_approved = True
                user.save()
                
                # Email notification for approval
                subject = 'Sua Conta foi Aprovada'
                message = f'Olá {user.get_full_name()}, sua conta foi aprovada. Você já pode fazer login e utilizar o sistema.'
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

                # Adicionar: Enviar notificação WhatsApp
                WhatsAppNotificationService.notify_user_approval(user)
                
                messages.success(request, f'Usuário {user.get_full_name()} foi aprovado com sucesso.')

            elif action == 'reject':
                # Optional: Email notification for rejection
                subject = 'Cadastro de Conta'
                message = f'Olá {user.get_full_name()}, seu cadastro não foi aprovado. Por favor, entre em contato com o administrador para mais informações.'
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

                # Adicionar: Enviar notificação WhatsApp
                WhatsAppNotificationService.notify_user_rejection(user)
                
                user.delete()  # Ou marcar como rejeitado ao invés de deletar
                messages.warning(request, f'Usuário {user.get_full_name()} foi rejeitado.')
        
        return redirect('pending_approvals')
    
    return render(request, 'pending_approvals.html', {'pending_users': pending_users})

@login_required
def profile_view(request):
    """Exibe o perfil do usuário"""
    user = request.user
    today = timezone.now().date()
    
    # Dados para estatísticas
    context = {
        'user': user,
        'recent_activities': []  # Placeholder para atividades recentes
    }
    
    # Estatísticas específicas por tipo de usuário
    if user.user_type == 'professor':
        # Total de aulas agendadas (futuras)
        total_scheduled = ScheduleRequest.objects.filter(
            professor=user,
            status='approved',
            scheduled_date__gte=today
        ).count()
        
        # Total de solicitações pendentes
        total_pending = ScheduleRequest.objects.filter(
            professor=user,
            status='pending'
        ).count()
        
        # Total de aulas já realizadas
        total_completed = ScheduleRequest.objects.filter(
            professor=user,
            status='approved',
            scheduled_date__lt=today
        ).count()
        
        context.update({
            'total_scheduled': total_scheduled,
            'total_pending': total_pending,
            'total_completed': total_completed
        })
    
    elif user.user_type == 'technician':
        # Total de solicitações aprovadas pelo técnico
        total_approved = ScheduleRequest.objects.filter(
            reviewed_by=user,
            status='approved'
        ).count()
        
        # Total de solicitações pendentes no sistema
        total_pending = ScheduleRequest.objects.filter(
            status='pending'
        ).count()
        
        # Número de laboratórios gerenciados (baseado no departamento)
        from scheduling.models import Laboratory
        # Removido is_active do filtro, substituído por departamento do usuário
        if user.lab_department:
            total_labs_managed = Laboratory.objects.filter(
                department=user.lab_department
            ).count()
        else:
            total_labs_managed = Laboratory.objects.count()
        
        context.update({
            'total_approved': total_approved,
            'total_pending': total_pending,
            'total_labs_managed': total_labs_managed
        })
    
    # Obter atividades recentes
    recent_activities = []
    
    # Exemplo: Últimos agendamentos para professores
    if user.user_type == 'professor':
        recent_schedules = ScheduleRequest.objects.filter(
            professor=user
        ).order_by('-request_date')[:5]
        
        for schedule in recent_schedules:
            activity = {
                'date': schedule.request_date,
                'description': f"Solicitou agendamento para o laboratório {schedule.laboratory.name} em {schedule.scheduled_date.strftime('%d/%m/%Y')}."
            }
            recent_activities.append(activity)
    
    # Exemplo: Últimas aprovações para técnicos
    elif user.user_type == 'technician':
        recent_reviews = ScheduleRequest.objects.filter(
            reviewed_by=user
        ).order_by('-review_date')[:5]
        
        for review in recent_reviews:
            action = "aprovou" if review.status == 'approved' else "rejeitou"
            activity = {
                'date': review.review_date,
                'description': f"{action.capitalize()} solicitação de {review.professor.get_full_name()} para o laboratório {review.laboratory.name}."
            }
            recent_activities.append(activity)
    
    context['recent_activities'] = recent_activities
    
    return render(request, 'profile.html', context)

@login_required
def profile_update(request):
    """Atualiza informações do perfil do usuário"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('profile')

@login_required
def change_password(request):
    """Altera a senha do usuário"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('profile')

def check_approval_status(request):
    """API endpoint to check if a user's approval status has changed"""
    if request.user.is_authenticated:
        return JsonResponse({
            'is_approved': request.user.is_approved
        })
    return JsonResponse({'is_approved': False}, status=401)
