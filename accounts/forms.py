# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

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