# whatsapp/services.py
from django.conf import settings
from .client import WhatsAppClient
import logging

logger = logging.getLogger(__name__)

class WhatsAppNotificationService:
    """
    Serviço para enviar notificações automáticas via WhatsApp
    baseadas nos mesmos templates de email
    """
    
    @staticmethod
    def send_notification(phone, message):
        """
        Envia uma notificação WhatsApp se o serviço estiver ativo
        
        Args:
            phone (str): Número do destinatário
            message (str): Conteúdo da mensagem
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        # Verificar se o serviço WhatsApp está ativado
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            return False
            
        if not phone:
            logger.warning("Tentativa de enviar mensagem sem número de telefone")
            return False
            
        # Enviar a mensagem
        client = WhatsAppClient()
        return client.send_message(phone, message)
    
    @staticmethod
    def notify_user_registration(user):
        """
        Envia notificação quando um usuário se registra
        
        Args:
            user: O usuário que se registrou
        """
        # Verificar se o serviço WhatsApp está ativado
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            return
            
        # Enviar notificação para o usuário
        if user.phone_number:
            message = f"""
*Confirmação de Cadastro - LabConnect*

Olá {user.get_full_name()},

Seu cadastro no sistema LabConnect foi recebido com sucesso e está sendo analisado.

Você receberá uma notificação quando sua conta for aprovada. Este processo geralmente leva de 24 a 48 horas úteis.

Atenciosamente,
Equipe LabConnect
            """.strip()
            
            WhatsAppNotificationService.send_notification(user.phone_number, message)
        
        # Notificar os laboratoristas
        from accounts.models import User
        technicians = User.objects.filter(user_type='technician', is_approved=True)
        
        for technician in technicians:
            if technician.phone_number:
                message = f"""
*Novo Usuário Registrado - LabConnect*

Um novo usuário se registrou no sistema LabConnect e aguarda aprovação:

*Nome:* {user.get_full_name()}
*Email:* {user.email}
*Tipo:* {user.get_user_type_display()}
*Telefone:* {user.phone_number}

Acesse o sistema para aprovar ou rejeitar esta solicitação.
                """.strip()
                
                WhatsAppNotificationService.send_notification(technician.phone_number, message)
    
    @staticmethod
    def notify_user_approval(user):
        """
        Envia notificação quando um usuário é aprovado
        
        Args:
            user: O usuário que foi aprovado
        """
        if not user.phone_number:
            return
            
        # Conteúdo específico com base no tipo de usuário
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
*Sua conta foi aprovada - LabConnect*

Olá {user.get_full_name()},

Sua conta no sistema LabConnect foi aprovada!

Agora você tem acesso completo à plataforma de acordo com seu perfil de {user.get_user_type_display()}.

{role_specific}

Atenciosamente,
Equipe LabConnect
        """.strip()
        
        WhatsAppNotificationService.send_notification(user.phone_number, message)
    
    @staticmethod
    def notify_user_rejection(user):
        """
        Envia notificação quando um usuário é rejeitado
        
        Args:
            user: O usuário que foi rejeitado
        """
        if not user.phone_number:
            return
            
        message = f"""
*Registro não aprovado - LabConnect*

Olá {user.get_full_name()},

Infelizmente, seu cadastro no sistema LabConnect não foi aprovado.

Isso pode ocorrer por diversas razões, como informações incompletas ou incorretas.

Para mais informações, entre em contato com um dos laboratoristas responsáveis.

Atenciosamente,
Equipe LabConnect
        """.strip()
        
        WhatsAppNotificationService.send_notification(user.phone_number, message)
    
    @staticmethod
    def notify_schedule_request(schedule_request):
        """
        Notifica laboratoristas sobre uma nova solicitação de agendamento
        
        Args:
            schedule_request: A solicitação de agendamento
        """
        # Buscar técnicos para notificar (filtrar por departamento do laboratório)
        from accounts.models import User
        department = schedule_request.laboratory.department.lower()
        
        technicians = User.objects.filter(
            user_type='technician', 
            is_approved=True
        )
        
        # Filtrar por departamento se o usuário tiver departamento configurado
        filtered_technicians = [tech for tech in technicians if 
                                tech.lab_department and tech.lab_department.lower() in department]
        
        # Se não houver técnicos do departamento específico, notificar todos
        if not filtered_technicians:
            filtered_technicians = technicians
        
        # Preparar a mensagem
        message = f"""
*Nova Solicitação de Agendamento*

Uma nova solicitação de agendamento foi registrada no sistema LabConnect.

*Professor:* {schedule_request.professor.get_full_name()}
*Laboratório:* {schedule_request.laboratory.name}
*Data:* {schedule_request.scheduled_date.strftime('%d/%m/%Y')}
*Horário:* {schedule_request.start_time.strftime('%H:%M')} - {schedule_request.end_time.strftime('%H:%M')}
*Disciplina:* {schedule_request.subject}

Acesse o sistema para revisar esta solicitação.
        """.strip()
        
        # Enviar para cada técnico filtrado
        for technician in filtered_technicians:
            if technician.phone_number:
                WhatsAppNotificationService.send_notification(technician.phone_number, message)
    
    @staticmethod
    def notify_schedule_approval(schedule_request):
        """
        Notifica o professor quando sua solicitação de agendamento é aprovada
        
        Args:
            schedule_request: A solicitação de agendamento aprovada
        """
        professor = schedule_request.professor
        if not professor.phone_number:
            return
        
        message = f"""
*Solicitação de Agendamento Aprovada*

Sua solicitação de agendamento foi aprovada.

*Laboratório:* {schedule_request.laboratory.name}
*Data:* {schedule_request.scheduled_date.strftime('%d/%m/%Y')}
*Horário:* {schedule_request.start_time.strftime('%H:%M')} - {schedule_request.end_time.strftime('%H:%M')}
*Disciplina:* {schedule_request.subject}

Para mais detalhes, acesse o sistema LabConnect.
        """.strip()
        
        WhatsAppNotificationService.send_notification(professor.phone_number, message)
    
    @staticmethod
    def notify_schedule_rejection(schedule_request):
        """
        Notifica o professor quando sua solicitação de agendamento é rejeitada
        
        Args:
            schedule_request: A solicitação de agendamento rejeitada
        """
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            return
        
        # Verificar se a notificação já foi enviada (previne duplicação)
        from django.core.cache import cache
        cache_key = f"whatsapp_notify_schedule_{schedule_request.id}"
        if cache.get(cache_key):
            # Notificação já foi enviada, não enviar novamente
            logger.info(f"Notificação de agendamento {schedule_request.id} já enviada. Ignorando.")
            return
        
        # Marcar como enviada para evitar duplicação
        cache.set(cache_key, True, timeout=3600)  # 1 hora de timeout

        professor = schedule_request.professor
        if not professor.phone_number:
            return
        
        rejection_reason = schedule_request.rejection_reason or "Não especificado"
        message = f"""
*Solicitação de Agendamento Rejeitada*

Sua solicitação de agendamento foi rejeitada.

*Laboratório:* {schedule_request.laboratory.name}
*Data:* {schedule_request.scheduled_date.strftime('%d/%m/%Y')}
*Horário:* {schedule_request.start_time.strftime('%H:%M')} - {schedule_request.end_time.strftime('%H:%M')}
*Disciplina:* {schedule_request.subject}

*Motivo da rejeição:* 
{rejection_reason}

Para mais informações, entre em contato com o laboratório ou crie uma nova solicitação.
        """.strip()
        
        WhatsAppNotificationService.send_notification(professor.phone_number, message)