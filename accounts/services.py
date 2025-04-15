# accounts/services.py
from django.core.mail import send_mail
from django.conf import settings

class EmailService:
    """Classe para gerenciar serviços de email do sistema"""
    
    @staticmethod
    def send_registration_notification(user):
        """
        Envia email de notificação quando um novo usuário se registra
        """
        subject = 'Registro no Sistema LabConnect'
        message = f"""
        Olá {user.get_full_name()},
        
        Seu cadastro no sistema LabConnect foi recebido com sucesso e está sendo analisado.
        
        Você receberá uma notificação quando sua conta for aprovada. Este processo geralmente leva de 24 a 48 horas úteis.
        
        Atenciosamente,
        Equipe LabConnect
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    @staticmethod
    def notify_technicians_new_user(user, technician_emails):
        """
        Notifica os laboratoristas sobre um novo registro
        """
        subject = 'Novo Usuário Registrado - LabConnect'
        message = f"""
        Um novo usuário se registrou no sistema LabConnect e aguarda aprovação:
        
        Nome: {user.get_full_name()}
        Email: {user.email}
        Tipo: {user.get_user_type_display()}
        Telefone: {user.phone_number}
        
        Acesse o sistema para aprovar ou rejeitar esta solicitação.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            technician_emails,
            fail_silently=False,
        )
    
    @staticmethod
    def send_approval_notification(user):
        """
        Notifica o usuário quando sua conta for aprovada
        """
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
        
        subject = 'Sua conta foi aprovada - LabConnect'
        message = f"""
        Olá {user.get_full_name()},
        
        Sua conta no sistema LabConnect foi aprovada!
        
        Agora você tem acesso completo à plataforma de acordo com seu perfil de {user.get_user_type_display()}.
        
        {role_specific}
        
        Atenciosamente,
        Equipe LabConnect
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    @staticmethod
    def send_rejection_notification(user_email, user_name):
        """
        Notifica o usuário quando sua conta for rejeitada
        """
        subject = 'Registro não aprovado - LabConnect'
        message = f"""
        Olá {user_name},
        
        Infelizmente, seu cadastro no sistema LabConnect não foi aprovado.
        
        Isso pode ocorrer por diversas razões, como informações incompletas ou incorretas.
        
        Para mais informações, entre em contato com um dos laboratoristas responsáveis.
        
        Atenciosamente,
        Equipe LabConnect
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )