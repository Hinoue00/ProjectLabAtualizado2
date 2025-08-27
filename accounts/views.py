# accounts/views.py

from datetime import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from scheduling.forms import PasswordChangeForm, ProfileUpdateForm
from scheduling.models import ScheduleRequest
from .forms import UserRegistrationForm, UserApprovalForm, ForgotPasswordForm, PasswordResetForm
from .models import User, PasswordResetRequest
from django.conf import settings
from django.http import JsonResponse
from django.core.cache import cache
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
        remember_me = request.POST.get('remember')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # Implementar funcionalidade "lembrar-me"
            if not remember_me:
                # Se não marcou "lembrar-me", sessão expira ao fechar o navegador
                request.session.set_expiry(0)
            else:
                # Se marcou "lembrar-me", sessão dura 30 dias
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 dias em segundos
            
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
    from django.core.cache import cache
    # Cache otimizado para lista de usuários pendentes
    cache_key = f'pending_users_{request.user.id}'
    pending_users = cache.get(cache_key)
    
    if pending_users is None:
        pending_users = list(User.objects.filter(is_approved=False).select_related().only(
            'id', 'first_name', 'last_name', 'email', 'phone_number', 
            'user_type', 'lab_department', 'registration_date'
        ))
        cache.set(cache_key, pending_users, 120)  # Cache por 2 minutos
    
    # Suporte a AJAX para atualizações em tempo real
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_id and action:
            try:
                user = User.objects.get(id=user_id)
                
                if action == 'approve':
                    user.is_approved = True
                    user.save()
                    

                    # Adicionar: Enviar notificação WhatsApp
                    WhatsAppNotificationService.notify_user_approval(user)
                    
                    messages.success(request, f'Usuário {user.get_full_name()} foi aprovado com sucesso.')

                elif action == 'reject':

                    # Adicionar: Enviar notificação WhatsApp
                    WhatsAppNotificationService.notify_user_rejection(user)
                    
                    user.delete()  # Ou marcar como rejeitado ao invés de deletar
                    messages.warning(request, f'Usuário {user.get_full_name()} foi rejeitado.')
                
                # Invalidar cache após mudanças
                cache.delete(f'pending_users_{request.user.id}')
                
                # Resposta AJAX ou redirect normal
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Usuário processado com sucesso!',
                        'action': action,
                        'user_id': user_id
                    })
                
            except User.DoesNotExist:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error': 'Usuário não encontrado'
                    }, status=404)
                messages.error(request, 'Usuário não encontrado')
        
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


# Views para Reset de Senha

def forgot_password_view(request):
    """View para solicitar reset de senha."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email, is_approved=True)
            
            # Verificar se já existe uma solicitação pendente
            existing_request = PasswordResetRequest.objects.filter(
                email=email,
                status__in=['pending', 'approved']
            ).first()
            
            if existing_request:
                messages.warning(
                    request, 
                    'Já existe uma solicitação de reset de senha pendente para este email.'
                )
                return redirect('forgot_password')
            
            # Criar nova solicitação
            import secrets
            from datetime import timedelta
            
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=24)  # Expira em 24 horas
            
            reset_request = PasswordResetRequest.objects.create(
                email=email,
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Enviar notificação WhatsApp para técnicos
            try:
                whatsapp_service = WhatsAppNotificationService()
                
                # Buscar todos os técnicos
                technicians = User.objects.filter(
                    user_type='technician', 
                    is_approved=True,
                    phone_number__isnull=False
                ).exclude(phone_number='')
                
                for technician in technicians:
                    message = f"""
🔑 *Nova Solicitação de Reset de Senha*

👤 Usuário: {user.get_full_name()}
📧 Email: {email}
🕐 Data: {reset_request.requested_at.strftime('%d/%m/%Y %H:%M')}

Para aprovar o reset, acesse o dashboard do sistema.
                    """.strip()
                    
                    whatsapp_service.send_message(
                        phone_number=technician.phone_number,
                        message=message
                    )
                
                messages.success(
                    request,
                    'Solicitação enviada com sucesso! Os técnicos foram notificados via WhatsApp.'
                )
                
            except Exception as e:
                messages.success(
                    request,
                    'Solicitação enviada com sucesso! Os técnicos serão notificados.'
                )
            
            return redirect('login')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'accounts/forgot_password.html', {'form': form})


def password_reset_view(request, token):
    """View para definir nova senha após aprovação do técnico."""
    try:
        reset_request = PasswordResetRequest.objects.get(
            token=token,
            status='approved'
        )
        
        # Verificar se não expirou
        if reset_request.is_expired:
            reset_request.status = 'expired'
            reset_request.save()
            messages.error(request, 'Este link de reset de senha expirou.')
            return redirect('forgot_password')
            
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Link de reset inválido ou expirado.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        form.initial['email'] = reset_request.email
        
        if form.is_valid():
            # Atualizar senha do usuário
            user = reset_request.user
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            # Marcar solicitação como concluída
            reset_request.status = 'completed'
            reset_request.save()
            
            messages.success(
                request,
                'Senha alterada com sucesso! Você pode fazer login com a nova senha.'
            )
            return redirect('login')
    else:
        form = PasswordResetForm(initial={'email': reset_request.email})
    
    context = {
        'form': form,
        'reset_request': reset_request
    }
    return render(request, 'accounts/password_reset.html', context)


@login_required
@user_passes_test(is_technician)
def password_reset_requests_view(request):
    """View para técnicos gerenciarem solicitações de reset."""
    pending_requests = PasswordResetRequest.objects.filter(
        status='pending'
    ).order_by('-requested_at')
    
    return render(request, 'accounts/password_reset_requests.html', {
        'pending_requests': pending_requests
    })


@login_required
@user_passes_test(is_technician)
def approve_password_reset(request, request_id):
    """Aprovam uma solicitação de reset de senha."""
    try:
        reset_request = PasswordResetRequest.objects.get(
            id=request_id,
            status='pending'
        )
        
        # Aprovar a solicitação
        reset_request.approve(request.user)
        
        # Enviar link via WhatsApp
        try:
            whatsapp_service = WhatsAppNotificationService()
            reset_url = request.build_absolute_uri(
                f"/password-reset/{reset_request.token}/"
            )
            
            message = f"""
🔑 *Solicitação de Reset de Senha Aprovada*

Olá {reset_request.user.get_full_name()},

Sua solicitação de reset de senha foi aprovada!

🔗 Clique no link abaixo para definir sua nova senha:
{reset_url}

⚠️ Este link expira em 24 horas.

Se você não solicitou este reset, ignore esta mensagem.
            """.strip()
            
            whatsapp_service.send_message(
                phone_number=reset_request.user.phone_number,
                message=message
            )
            
            reset_request.whatsapp_sent = True
            reset_request.whatsapp_sent_at = timezone.now()
            reset_request.save()
            
            messages.success(
                request,
                f'Solicitação aprovada! Link enviado via WhatsApp para {reset_request.user.get_full_name()}.'
            )
            
        except Exception as e:
            messages.warning(
                request,
                f'Solicitação aprovada, mas houve erro ao enviar WhatsApp: {str(e)}'
            )
            
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada.')
    
    return redirect('password_reset_requests')


@login_required
@user_passes_test(is_technician)
def reject_password_reset(request, request_id):
    """Rejeita uma solicitação de reset de senha."""
    try:
        reset_request = PasswordResetRequest.objects.get(
            id=request_id,
            status='pending'
        )
        
        reset_request.status = 'rejected'
        reset_request.approved_by = request.user
        reset_request.approved_at = timezone.now()
        reset_request.save()
        
        messages.success(
            request,
            f'Solicitação de {reset_request.user.get_full_name()} foi rejeitada.'
        )
        
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Solicitação não encontrada.')
    
    return redirect('password_reset_requests')


