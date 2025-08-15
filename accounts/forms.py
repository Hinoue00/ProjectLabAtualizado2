# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, PasswordResetRequest

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 
                 'user_type', 'password1', 'password2')
                 
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validar domínios de email permitidos
            domain = email.split('@')[-1].lower()
            allowed_domains = ['cogna.com.br', 'kroton.com.br']
            if domain not in allowed_domains:
                raise forms.ValidationError(
                    'Apenas emails corporativos são permitidos (@cogna.com.br e @kroton.com.br)'
                )
        return email

class UserApprovalForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('is_approved',)


class ForgotPasswordForm(forms.Form):
    """Formulário para solicitar reset de senha."""
    
    email = forms.EmailField(
        label='Email Corporativo',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu.email@cogna.com.br ou @kroton.com.br',
            'autofocus': True
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validar domínios de email permitidos
            domain = email.split('@')[-1].lower()
            allowed_domains = ['cogna.com.br', 'kroton.com.br']
            if domain not in allowed_domains:
                raise forms.ValidationError(
                    'Apenas emails corporativos são permitidos (@cogna.com.br e @kroton.com.br)'
                )
            
            # Verificar se o email existe no sistema
            try:
                User.objects.get(email=email, is_approved=True)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    'Este email não está cadastrado no sistema ou não foi aprovado.'
                )
        return email


class PasswordResetForm(forms.Form):
    """Formulário para definir nova senha após aprovação."""
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True
        })
    )
    
    password1 = forms.CharField(
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua nova senha'
        })
    )
    
    password2 = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme sua nova senha'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('As senhas não coincidem.')
        
        # Validar força da senha
        if password1 and len(password1) < 8:
            raise forms.ValidationError('A senha deve ter pelo menos 8 caracteres.')
        
        return cleaned_data