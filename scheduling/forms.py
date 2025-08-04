# scheduling/forms.py
from django import forms
from .models import ScheduleRequest, Laboratory, User
from inventory.models import Material
from django.utils import timezone
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from datetime import datetime, timedelta, time
from django.core.validators import FileExtensionValidator
from accounts.services import UserService
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

class TimeInput(forms.TimeInput):
    input_type = 'time'

class DateInput(forms.DateInput):
    input_type = 'date'

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        # No establecemos el widget aquí
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({'multiple': 'multiple'})

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ScheduleRequestForm(forms.ModelForm):

    attachments = forms.FileField(
        required=False,
        help_text="Você pode anexar roteiros de aula, imagens ou qualquer outro documento."
    )

    guide_file = forms.FileField(
        required=False,
        help_text="Você pode anexar o roteiro de aula (PDF, DOC, DOCX, ODT).",
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'odt'])]
    )

    SHIFT_CHOICES = (
        ('morning', 'Matutino (08:00 - 12:00)'),
        ('evening', 'Noturno (19:00 - 22:00)'),
    )
    
    shift = forms.ChoiceField(choices=SHIFT_CHOICES, label="Turno", required=True)
    
    selected_materials = forms.ModelMultipleChoiceField(
        queryset=Material.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Materiais Necessários",
        help_text="Selecione os materiais que você pretende usar na aula"
    )
    
    class_semester = forms.CharField(
        max_length=20,
        required=False,
        label="Semestre/Turma",
        help_text="Ex: 1º Semestre, 3º Período, Turma A",
        widget=forms.TextInput(attrs={'placeholder': 'Ex: 1º Semestre'})
    )
    
    class Meta:
        model = ScheduleRequest
        fields = [
            'laboratory', 'subject', 'description', 
            'scheduled_date', 'shift',  # Substituímos start_time e end_time por shift 
            'number_of_students', 'class_semester', 'materials', 'selected_materials',
            'guide_file',
        ]
        widgets = {
            'scheduled_date': DateInput(),
            'description': forms.Textarea(attrs={'rows': 4, 'required': False}),
            'materials': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Liste os materiais necessários para a aula...'}),
        }

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas laboratórios ativos
        self.fields['laboratory'].queryset = Laboratory.objects.filter(is_active=True)
        
        # Inicializar queryset de materiais vazio
        self.fields['selected_materials'].queryset = Material.objects.none()
        
        # Adiciona classes Bootstrap aos campos
        for field_name, field in self.fields.items():
            if field_name != 'selected_materials':  # Excluir checkboxes
                field.widget.attrs['class'] = 'form-control'
            
        # Aplica limites de data (próxima semana - segunda a sábado)
        today = timezone.now().date()
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado

        # Configurar o campo de data para permitir segunda a sábado
        # Mas flexibilizar quando editando um rascunho existente
        instance = kwargs.get('instance')
        if instance and hasattr(instance, 'scheduled_date') and instance.scheduled_date:
            # Se editando rascunho, permitir datas mais flexíveis (incluindo a data atual do rascunho)
            min_date = min(instance.scheduled_date, next_week_start)
            max_date = max(instance.scheduled_date, next_week_end)
            self.fields['scheduled_date'].widget.attrs.update({
                'min': min_date,
                'max': max_date,
            })
        else:
            # Para novos agendamentos, manter restrição original
            self.fields['scheduled_date'].widget.attrs.update({
                'min': next_week_start,
                'max': next_week_end,
            })

        # Se estamos editando um agendamento existente, preencher o campo de turno
        if instance:
            # Priorizar campo shift se existir
            if hasattr(instance, 'shift') and instance.shift:
                self.initial['shift'] = instance.shift
            elif hasattr(instance, 'start_time') and instance.start_time:
                # Determinar turno baseado no horário
                start_hour = instance.start_time.hour
                if 7 <= start_hour < 12:
                    self.initial['shift'] = 'morning'
                elif 12 <= start_hour < 18:
                    self.initial['shift'] = 'afternoon'
                else:
                    self.initial['shift'] = 'evening'

    def clean_scheduled_date(self):
        """Valida que a data é em um dia de semana (segunda a sábado)"""
        date = self.cleaned_data.get('scheduled_date')
        
        if date:
            if date.weekday() == 6:  # 6=domingo (0=segunda, 1=terça, ..., 5=sábado, 6=domingo)
                raise forms.ValidationError("Domingo não é permitido para agendamentos.")
                
            # Valida que a data está na próxima semana
            today = timezone.now().date()
            next_week_start = today + timedelta(days=(7 - today.weekday()))
            next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado
            
            if not (next_week_start <= date <= next_week_end):
                raise forms.ValidationError("Os agendamentos só podem ser realizados para a próxima semana (segunda a sábado).")
        
        return date
    
    def save(self, commit=True):
        """Sobrescreve o método save para definir os horários baseados no turno selecionado"""
        instance = super().save(commit=False)
        
        # Define os horários baseados no turno selecionado
        shift = self.cleaned_data.get('shift')
        
        if shift == 'morning':
            instance.start_time = time(8, 0)  # 8:00 AM
            instance.end_time = time(12, 0)   # 12:00 PM
        elif shift == 'evening':
            instance.start_time = time(19, 0)  # 7:00PM
            instance.end_time = time(22, 0)    # 10:00 PM
        
        if commit:
            instance.save()
        
        return instance
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        scheduled_date = cleaned_data.get('scheduled_date')
        number_of_students = cleaned_data.get('number_of_students')
        laboratory = cleaned_data.get('laboratory')
        
        # Verifica se a data está preenchida
        if not scheduled_date:
            return cleaned_data
        
        # Verifica se a data está na próxima semana
        today = timezone.now().date()
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=6)
        
        if not (next_week_start <= scheduled_date <= next_week_end):
            self.add_error('scheduled_date', 'Os agendamentos só podem ser realizados para a próxima semana.')
        
        # Verifica se o horário de término é posterior ao início
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'O horário de término deve ser posterior ao horário de início.')
        
        # Verifica se o número de alunos não excede a capacidade do laboratório
        if laboratory and number_of_students:
            if number_of_students > laboratory.capacity:
                self.add_error('number_of_students', 
                              f'O número de alunos excede a capacidade do laboratório ({laboratory.capacity}).')
        
        return cleaned_data
    
class ProfileUpdateForm(forms.ModelForm):
    """Formulário aprimorado para atualização de perfil"""
    
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        error_messages={
            'required': 'Por favor, informe seu nome.',
            'max_length': 'O nome deve ter no máximo 30 caracteres.'
        }
    )
    
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        error_messages={
            'required': 'Por favor, informe seu sobrenome.',
            'max_length': 'O sobrenome deve ter no máximo 30 caracteres.'
        }
    )
    
    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Por favor, informe seu email corporativo.',
            'invalid': 'Por favor, informe um email válido.'
        }
    )
    
    phone_number = forms.CharField(
        max_length=20, 
        required=True,
        error_messages={
            'required': 'Por favor, informe seu número de telefone.',
            'max_length': 'O telefone deve ter no máximo 20 caracteres.'
        }
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'lab_department')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tornar lab_department opcional
        if 'lab_department' in self.fields:
            self.fields['lab_department'].required = False
        
        # Adicionar textos de ajuda
        self.fields['email'].help_text = "Use seu email corporativo (@cogna.com.br ou @kroton.com.br)."
        self.fields['phone_number'].help_text = "Digite apenas números, incluindo DDD."
    
    def clean_email(self):
        """Validação avançada de email"""
        email = self.cleaned_data.get('email')
        
        if email:
            # Usar o serviço para validar o domínio do email
            is_valid, message = UserService.validate_corporate_email(email)
            if not is_valid:
                raise forms.ValidationError(message)
                
            # Verificar se o email já existe (excluindo o usuário atual)
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Este email já está em uso.')
        
        return email
    
    def clean_phone_number(self):
        """Validação de número de telefone"""
        phone = self.cleaned_data.get('phone_number')
        
        if phone:
            # Remover caracteres não numéricos
            phone = ''.join(filter(str.isdigit, phone))
            
            # Validar formato do telefone
            if len(phone) < 10 or len(phone) > 11:
                raise forms.ValidationError('O telefone deve ter 10 ou 11 dígitos, incluindo o DDD.')
        
        return phone
    
    def clean(self):
        """Validação global do formulário"""
        cleaned_data = super().clean()
        
        # Verificar se o usuário é técnico e tem departamento preenchido
        user_type = self.instance.user_type
        lab_department = cleaned_data.get('lab_department')
        
        if user_type == 'technician' and not lab_department:
            self.add_error('lab_department', 'Técnicos devem selecionar um departamento.')
        
        return cleaned_data

class PasswordChangeForm(DjangoPasswordChangeForm):
    """Formulário aprimorado para alteração de senha"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Melhorar rótulos e textos de ajuda
        self.fields['old_password'].label = 'Senha Atual'
        self.fields['old_password'].help_text = 'Digite sua senha atual para verificação.'
        
        self.fields['new_password1'].label = 'Nova Senha'
        self.fields['new_password1'].help_text = 'Sua senha deve ter pelo menos 8 caracteres, incluindo letras e números.'
        
        self.fields['new_password2'].label = 'Confirmação da Nova Senha'
        self.fields['new_password2'].help_text = 'Digite a nova senha novamente para verificação.'
        
        # Adicionar classes CSS
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'auth-input'})
    
    def clean_new_password1(self):
        """Validação avançada da nova senha"""
        password = self.cleaned_data.get('new_password1')
        
        if password:
            # Verificar complexidade
            if len(password) < 8:
                raise forms.ValidationError('A senha deve ter pelo menos 8 caracteres.')
            
            if not any(char.isdigit() for char in password):
                raise forms.ValidationError('A senha deve conter pelo menos um número.')
                
            if not any(char.isalpha() for char in password):
                raise forms.ValidationError('A senha deve conter pelo menos uma letra.')
            
            # Verificar se a nova senha é diferente da senha atual
            if self.user.check_password(password):
                raise forms.ValidationError('A nova senha deve ser diferente da senha atual.')
            
            # Usar validador padrão do Django
            try:
                validate_password(password, self.user)
            except ValidationError as error:
                self.add_error('new_password1', error)
        
        return password
    
    def clean(self):
        """Validação global do formulário"""
        cleaned_data = super().clean()
        
        # Verificar se as senhas coincidem
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', 'As senhas não coincidem.')
        
        return cleaned_data