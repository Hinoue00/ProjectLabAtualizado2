
# accounts/services.py
from django.contrib.auth import authenticate, login
from django.conf import settings
from .models import User
from whatsapp.services import WhatsAppNotificationService
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Classe de serviço para operações relacionadas a usuários"""
    
    @staticmethod
    def authenticate_user(request, email, password):
        """Autentica um usuário e faz o login"""
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return True
        return False
    
    @staticmethod
    def register_user(form_data):
        """Registra um novo usuário e envia notificação por WhatsApp"""
        user = form_data.save(commit=False)
        user.is_active = True
        user.save()
        
        # Envia notificação por WhatsApp
        try:
            WhatsAppNotificationService.notify_user_registration(user)
        except Exception as e:
            logger.error(f"Erro ao enviar notificação WhatsApp de registro: {str(e)}")
            
        return user
    
    @staticmethod
    def approve_user(user_id):
        """Aprova a conta de um usuário e notifica por WhatsApp"""
        try:
            user = User.objects.get(id=user_id)
            user.is_approved = True
            user.save()
            
            # Notifica o usuário por WhatsApp
            try:
                WhatsAppNotificationService.notify_user_approval(user)
            except Exception as e:
                logger.error(f"Erro ao enviar notificação WhatsApp de aprovação: {str(e)}")
                
            return user
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def reject_user(user_id):
        """Rejeita a conta de um usuário e notifica por WhatsApp"""
        try:
            user = User.objects.get(id=user_id)
            user_name = user.get_full_name()
            user_phone = user.phone_number
            
            # Notifica o usuário por WhatsApp antes de marcar como inativo
            try:
                WhatsAppNotificationService.notify_user_rejection(user)
            except Exception as e:
                logger.error(f"Erro ao enviar notificação WhatsApp de rejeição: {str(e)}")
            
            # Marca como inativo ao invés de excluir
            user.is_active = False
            user.save()
            
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def notify_technicians_new_user(user):
        """Notifica técnicos sobre novo registro via WhatsApp"""
        technicians = User.objects.filter(
            user_type='technician', 
            is_approved=True
        )
        
        for technician in technicians:
            try:
                WhatsAppNotificationService.notify_technician_new_user(technician, user)
            except Exception as e:
                logger.error(f"Erro ao notificar técnico {technician.id} sobre novo usuário: {str(e)}")
    
    @staticmethod
    def validate_corporate_email(email):
        """
        Valida se o email é de um domínio corporativo permitido
        Retorna (booleano, mensagem)
        """
        if not email:
            return False, "Email não pode estar vazio"
            
        domain = email.split('@')[-1].lower()
        allowed_domains = ['cogna.com.br', 'kroton.com.br']
        
        if domain not in allowed_domains:
            return False, "Apenas emails corporativos são permitidos (@cogna.com.br e @kroton.com.br)"
        
        return True, ""
    
    @staticmethod
    def get_user_statistics(user):
        """
        Obtém estatísticas para exibição no perfil do usuário
        """
        from django.utils import timezone
        from django.db.models import Count, Q
        
        today = timezone.now().date()
        stats = {}
        
        # Estatísticas específicas para cada tipo de usuário
        if user.user_type == 'professor':
            from scheduling.models import ScheduleRequest
            
            # Usando agregação para obter todas as contagens em uma única consulta
            request_stats = ScheduleRequest.objects.filter(professor=user).aggregate(
                total_scheduled=Count('id', filter=Q(status='approved', scheduled_date__gte=today)),
                total_pending=Count('id', filter=Q(status='pending')),
                total_completed=Count('id', filter=Q(status='approved', scheduled_date__lt=today))
            )
            
            stats.update(request_stats)
            
        elif user.user_type == 'technician':
            from scheduling.models import ScheduleRequest, Laboratory
            
            # Estatísticas de aprovação
            approval_stats = ScheduleRequest.objects.aggregate(
                total_approved=Count('id', filter=Q(reviewed_by=user, status='approved')),
                total_pending=Count('id', filter=Q(status='pending'))
            )
            
            # Laboratórios gerenciados
            if user.lab_department:
                total_labs_managed = Laboratory.objects.filter(department=user.lab_department).count()
            else:
                total_labs_managed = Laboratory.objects.count()
            
            stats.update(approval_stats)
            stats['total_labs_managed'] = total_labs_managed
        
        return stats
  