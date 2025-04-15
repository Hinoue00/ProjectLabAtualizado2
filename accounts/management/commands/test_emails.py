from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import User
from accounts.services import EmailService

class Command(BaseCommand):
    help = 'Testa o envio de emails do sistema LabConnect'

    def add_arguments(self, parser):
        parser.add_argument('--to', type=str, help='Email destino para teste')
        parser.add_argument('--type', type=str, choices=['registration', 'approval', 'rejection', 'notification'], 
                            default='registration', help='Tipo de email para teste')

    def handle(self, *args, **options):
        test_email = options.get('to')
        email_type = options.get('type')
        
        if not test_email:
            test_email = input("Digite o email de destino para o teste: ")
        
        # Criar um usuário fictício para teste
        test_user = User(
            first_name="Usuário",
            last_name="de Teste",
            email=test_email,
            user_type="professor",
            phone_number="99999999999",
            is_approved=False
        )
        
        if email_type == 'registration':
            self.stdout.write(self.style.HTTP_INFO('Testando email de confirmação de registro...'))
            EmailService.send_registration_notification(test_user)
            
        elif email_type == 'approval':
            self.stdout.write(self.style.HTTP_INFO('Testando email de aprovação de conta...'))
            test_user.is_approved = True
            EmailService.send_approval_notification(test_user)
            
        elif email_type == 'rejection':
            self.stdout.write(self.style.HTTP_INFO('Testando email de rejeição de conta...'))
            EmailService.send_rejection_notification(test_email, test_user.get_full_name())
            
        elif email_type == 'notification':
            self.stdout.write(self.style.HTTP_INFO('Testando email de notificação para técnicos...'))
            EmailService.notify_technicians_new_user(test_user, [test_email])
        
        self.stdout.write(self.style.SUCCESS(f'Email de teste enviado para {test_email}'))
        self.stdout.write(
            self.style.WARNING('Nota: Se você estiver usando o backend de console, o email aparecerá no terminal.')
        )