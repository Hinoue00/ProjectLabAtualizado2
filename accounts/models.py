# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Define um gerenciador de modelo para User com email como campo único de identificação."""

    def create_user(self, email, password=None, **extra_fields):
        """Cria e salva um usuário com o email e senha fornecidos."""
        if not email:
            raise ValueError('O Email deve ser definido')
            
        # Validar domínios de email permitidos
        domain = email.split('@')[-1].lower()
        allowed_domains = ['cogna.com.br', 'kroton.com.br']
        if domain not in allowed_domains:
            raise ValueError('Apenas emails corporativos são permitidos (@cogna.com.br e @kroton.com.br')
            
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Cria e salva um SuperUser com o email e senha fornecidos."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)  # Superuser sempre é aprovado

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('professor', 'Professor'),
        ('technician', 'Laboratorista'),
    )
    
    username = None  # Remove username
    email = models.EmailField(_('email address'), unique=True)  # Torna email único
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=20)
    is_approved = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True)
    lab_department = models.CharField(max_length=100, blank=True, null=True, 
                                    help_text="Department for technicians (e.g., 'engineering', 'health', 'computer')")

    USERNAME_FIELD = 'email'  # Define email como campo de identificação
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']  # Remove username dos campos obrigatórios

    objects = UserManager()  # Usa o gerenciador personalizado

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_user_type_display()})"
    
    def has_corporate_email(self):
        """Verifica se o usuário possui um email corporativo válido"""
        if not self.email:
            return False
            
        domain = self.email.split('@')[-1].lower()
        allowed_domains = ['cogna.com.br', 'kroton.com.br']
        
        return domain in allowed_domains