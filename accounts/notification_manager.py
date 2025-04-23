# accounts/notification_manager.py
from django.conf import settings
import logging
from .services import EmailService
from .whatsapp_unofficial_service import WhatsAppUnofficialService

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Gerenciador unificado para todas as notificações do sistema (email, WhatsApp, etc.)
    """
    
    @staticmethod
    def send_registration_notification(user):
        """
        Envia notificações de registro por todos os canais configurados
        """
        success = True
        
        # Enviar notificação por email se habilitado
        if getattr(settings, 'USE_EMAIL_NOTIFICATIONS', True):
            try:
                EmailService.send_registration_notification(user)
            except Exception as e:
                logger.error(f"Falha ao enviar email de registro: {str(e)}")
                success = False
        
        # Enviar notificação por WhatsApp se habilitado
        if getattr(settings, 'USE_WHATSAPP_NOTIFICATIONS', False):
            try:
                whatsapp_success = WhatsAppUnofficialService.send_message(
                    user.phone_number,
                    f"""
                    Olá {user.get_full_name()},
                    
                    Seu cadastro no sistema LabConnect foi recebido com sucesso e está sendo analisado.
                    
                    Você receberá uma notificação quando sua conta for aprovada. Este processo geralmente leva de 24 a 48 horas úteis.
                    
                    Atenciosamente,
                    Equipe LabConnect
                    """
                )
                if not whatsapp_success:
                    success = False
            except Exception as e:
                logger.error(f"Falha ao enviar WhatsApp de registro: {str(e)}")
                success = False
        
        return success
    
    @staticmethod
    def notify_technicians_new_user(user, technician_emails=None, technician_phones=None):
        """
        Notifica os técnicos sobre um novo registro de usuário
        """
        success = True
        
        # Enviar notificação por email se habilitado
        if getattr(settings, 'USE_EMAIL_NOTIFICATIONS', True) and technician_emails:
            try:
                EmailService.notify_technicians_new_user(user, technician_emails)
            except Exception as e:
                logger.error(f"Falha ao enviar email de notificação para técnicos: {str(e)}")
                success = False
        
        # Enviar notificação por WhatsApp se habilitado
        if getattr(settings, 'USE_WHATSAPP_NOTIFICATIONS', False) and technician_phones:
            message = f"""
            Um novo usuário se registrou no sistema LabConnect e aguarda aprovação:
            
            Nome: {user.get_full_name()}
            Email: {user.email}
            Tipo: {user.get_user_type_display()}
            Telefone: {user.phone_number}
            
            Acesse o sistema para aprovar ou rejeitar esta solicitação.
            """
            
            for phone in technician_phones:
                try:
                    if not WhatsAppUnofficialService.send_message(phone, message):
                        success = False
                except Exception as e:
                    logger.error(f"Falha ao enviar WhatsApp de notificação para técnico: {str(e)}")
                    success = False
        
        return success
    
    @staticmethod
    def send_approval_notification(user):
        """
        Envia notificação de aprovação por todos os canais configurados
        """
        success = True
        
        # Enviar notificação por email se habilitado
        if getattr(settings, 'USE_EMAIL_NOTIFICATIONS', True):
            try:
                EmailService.send_approval_notification(user)
            except Exception as e:
                logger.error(f"Falha ao enviar email de aprovação: {str(e)}")
                success = False
        
        # Enviar notificação por WhatsApp se habilitado
        if getattr(settings, 'USE_WHATSAPP_NOTIFICATIONS', False):
            # Conteúdo específico para o tipo de usuário
            role_specific = ""
            
            if user.user_type == 'professor':
                role_specific = """
                Como professor, você pode agendar laboratórios para suas aulas, visualizar disponibilidade,
                e solicitar materiais necessários. Lembre-se que os agendamentos só podem ser feitos às 
                quintas e sextas-feiras para a semana seguinte.
                """
            else:  # technician
                role_specific = """
                Como laboratorista, você pode gerenciar agendamentos, controlar o inventário de materiais,
                e aprovar solicitações de professores. Você também terá acesso aos relatórios e estatísticas
                do sistema.
                """
            
            message = f"""
            Olá {user.get_full_name()},
            
            Sua conta no sistema LabConnect foi aprovada!
            
            Agora você tem acesso completo à plataforma de acordo com seu perfil de {user.get_user_type_display()}.
            
            {role_specific}
            
            Atenciosamente,
            Equipe LabConnect
            """
            
            try:
                whatsapp_success = WhatsAppUnofficialService.send_message(user.phone_number, message)
                if not whatsapp_success:
                    success = False
            except Exception as e:
                logger.error(f"Falha ao enviar WhatsApp de aprovação: {str(e)}")
                success = False
        
        return success
    
    @staticmethod
    def send_rejection_notification(user_email, user_phone, user_name):
        """
        Envia notificação de rejeição por todos os canais configurados
        """
        success = True
        
        # Enviar notificação por email se habilitado
        if getattr(settings, 'USE_EMAIL_NOTIFICATIONS', True):
            try:
                EmailService.send_rejection_notification(user_email, user_name)
            except Exception as e:
                logger.error(f"Falha ao enviar email de rejeição: {str(e)}")
                success = False
        
        # Enviar notificação por WhatsApp se habilitado
        if getattr(settings, 'USE_WHATSAPP_NOTIFICATIONS', False):
            message = f"""
            Olá {user_name},
            
            Infelizmente, seu cadastro no sistema LabConnect não foi aprovado.
            
            Isso pode ocorrer por diversas razões, como informações incompletas ou incorretas.
            
            Para mais informações, entre em contato com um dos laboratoristas responsáveis.
            
            Atenciosamente,
            Equipe LabConnect
            """
            
            try:
                whatsapp_success = WhatsAppUnofficialService.send_message(user_phone, message)
                if not whatsapp_success:
                    success = False
            except Exception as e:
                logger.error(f"Falha ao enviar WhatsApp de rejeição: {str(e)}")
                success = False
        
        return success