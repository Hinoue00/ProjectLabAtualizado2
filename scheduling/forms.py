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
    
    def format_value(self, value):
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value)

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
    
    shift = forms.ChoiceField(choices=SHIFT_CHOICES, label="Turno", required=False)
    
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
            'scheduled_date': DateInput(attrs={'required': False}),
            'description': forms.Textarea(attrs={'rows': 4, 'required': False}),
            'materials': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Liste os materiais necessários para a aula...', 'required': False}),
            'subject': forms.TextInput(attrs={'required': False}),
        }

    
    def __init__(self, *args, **kwargs):
        # Extrair parâmetro is_draft se fornecido
        self.is_draft = kwargs.pop('is_draft', False)
        super().__init__(*args, **kwargs)
        
        # Obter instância se existir (antes de usar)
        instance = kwargs.get('instance')
        
        # Filtra apenas laboratórios ativos que não sejam de estoque
        self.fields['laboratory'].queryset = Laboratory.objects.filter(is_active=True, is_storage=False)
        
        # Inicializar queryset de materiais vazio
        self.fields['selected_materials'].queryset = Material.objects.none()
        
        # Tornar todos os campos não obrigatórios
        for field_name, field in self.fields.items():
            field.required = False
        
        # Adiciona classes Bootstrap aos campos
        for field_name, field in self.fields.items():
            if field_name != 'selected_materials':  # Excluir checkboxes
                field.widget.attrs['class'] = 'form-control'
                # Preservar atributos especiais do campo de data
                if field_name == 'scheduled_date' and hasattr(field.widget, 'input_type'):
                    field.widget.attrs['type'] = field.widget.input_type
            
        # Configurar limites de data baseado no tipo (rascunho vs solicitação)
        today = timezone.now().date()
        
        if self.is_draft:
            # Para RASCUNHOS: permitir o mês inteiro
            month_start = today.replace(day=1)
            # Último dia do mês atual
            if today.month == 12:
                month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            self.fields['scheduled_date'].widget.attrs.update({
                'min': month_start.strftime('%Y-%m-%d'),
                'max': month_end.strftime('%Y-%m-%d'),
            })
        else:
            # Para SOLICITAÇÕES FINAIS: próxima semana (segunda a sábado)
            next_week_start = today + timedelta(days=(7 - today.weekday()))
            next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado
            
            # Configurar o campo de data para permitir segunda a sábado
            # Mas flexibilizar quando editando um rascunho existente
            if instance and hasattr(instance, 'scheduled_date') and instance.scheduled_date:
                # Se editando, permitir datas mais flexíveis (incluindo a data atual)
                min_date = min(instance.scheduled_date, next_week_start)
                max_date = max(instance.scheduled_date, next_week_end)
                self.fields['scheduled_date'].widget.attrs.update({
                    'min': min_date.strftime('%Y-%m-%d'),
                    'max': max_date.strftime('%Y-%m-%d'),
                })
            else:
                # Para novos agendamentos, manter restrição da próxima semana
                self.fields['scheduled_date'].widget.attrs.update({
                    'min': next_week_start.strftime('%Y-%m-%d'),
                    'max': next_week_end.strftime('%Y-%m-%d'),
                })

        # Se estamos editando uma instância existente, preencher o campo de turno
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
        """Valida data baseado no tipo: rascunho (mês inteiro) vs solicitação (próxima semana)"""
        date = self.cleaned_data.get('scheduled_date')
        
        # Se não informar data, não há problema
        if not date:
            return date
            
        if date:
            # Domingo nunca é permitido
            if date.weekday() == 6:  # 6=domingo
                raise forms.ValidationError("Domingo não é permitido para agendamentos.")
            
            today = timezone.now().date()
            
            if self.is_draft:
                # Para RASCUNHOS: permitir qualquer data do mês atual
                month_start = today.replace(day=1)
                if today.month == 12:
                    month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                
                if not (month_start <= date <= month_end):
                    raise forms.ValidationError("Para rascunhos, você pode agendar para qualquer data do mês atual.")
            else:
                # Para SOLICITAÇÕES FINAIS: apenas próxima semana (segunda a sábado)
                next_week_start = today + timedelta(days=(7 - today.weekday()))
                next_week_end = next_week_start + timedelta(days=5)  # Segunda a sábado
                
                if not (next_week_start <= date <= next_week_end):
                    raise forms.ValidationError("Os agendamentos só podem ser realizados para a próxima semana (segunda a sábado).")
        
        return date
    
    def save(self, commit=True):
        """Sobrescreve o método save para definir os horários baseados no turno selecionado"""
        instance = super().save(commit=False)
        
        # Define os horários baseados no turno selecionado (apenas se turno foi informado)
        shift = self.cleaned_data.get('shift')
        
        if shift == 'morning':
            instance.start_time = time(8, 0)  # 8:00 AM
            instance.end_time = time(12, 0)   # 12:00 PM
        elif shift == 'evening':
            instance.start_time = time(19, 0)  # 7:00PM
            instance.end_time = time(22, 0)    # 10:00 PM
        # Se não informar turno, deixa os horários como estão (podem ser None)
        
        if commit:
            instance.save()
        
        return instance
    
    def clean_number_of_students(self):
        """Validação específica do número de alunos"""
        number_of_students = self.cleaned_data.get('number_of_students')
        
        if number_of_students is not None:
            if number_of_students <= 0:
                raise forms.ValidationError("O número de alunos deve ser maior que zero.")
            if number_of_students > 100:
                raise forms.ValidationError("O número de alunos não pode exceder 100.")
        
        return number_of_students

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        scheduled_date = cleaned_data.get('scheduled_date')
        number_of_students = cleaned_data.get('number_of_students')
        laboratory = cleaned_data.get('laboratory')
        
        # Validações agora são opcionais - apenas se os campos estiverem preenchidos
        
        # Validação de data já é feita no clean_scheduled_date() com base no is_draft
        
        # Verifica se o horário de término é posterior ao início (apenas se ambos informados)
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'O horário de término deve ser posterior ao horário de início.')
        
        # Verifica se o número de alunos não excede a capacidade do laboratório (apenas se ambos informados)
        if laboratory and number_of_students and hasattr(laboratory, 'capacity') and laboratory.capacity:
            if number_of_students > laboratory.capacity:
                self.add_error('number_of_students', 
                              f'O número de alunos ({number_of_students}) excede a capacidade do laboratório ({laboratory.capacity} pessoas).')
        
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

class ExceptionScheduleRequestForm(forms.ModelForm):
    """
    Formulário especial para técnicos criarem agendamentos de exceção
    para professores em dias/horários não liberados normalmente
    """
    
    professor = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='professor', is_approved=True),
        label="Professor",
        help_text="Selecione o professor para quem está criando o agendamento de exceção",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    exception_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Explique o motivo desta exceção...'}),
        label="Motivo da Exceção",
        help_text="Descreva detalhadamente o motivo para este agendamento excepcional",
        max_length=500
    )
    
    PERIOD_CHOICES = [
        ('matutino', 'Período Matutino (7h às 12h)'),
        ('noturno', 'Período Noturno (19h às 23h)'),
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Período",
        help_text="Selecione o período para o agendamento de exceção"
    )
    
    guide_file = forms.FileField(
        required=False,
        help_text="Roteiro de aula (PDF, DOC, DOCX, ODT)",
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'odt'])],
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ScheduleRequest
        fields = [
            'professor', 'laboratory', 'subject', 'description', 
            'scheduled_date', 'period',
            'number_of_students', 'class_semester', 'materials',
            'exception_reason', 'guide_file'
        ]
        widgets = {
            'scheduled_date': DateInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'materials': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Liste os materiais necessários...'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'number_of_students': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'class_semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1º Semestre'}),
        }

    def __init__(self, *args, **kwargs):
        # Extrair o técnico que está criando o agendamento
        self.technician = kwargs.pop('technician', None)
        super().__init__(*args, **kwargs)
        
        # Configurar laboratórios ativos que não sejam de estoque
        self.fields['laboratory'].queryset = Laboratory.objects.filter(is_active=True, is_storage=False)
        self.fields['laboratory'].widget.attrs['class'] = 'form-control'
        
        # Configurar professores ativos e aprovados
        self.fields['professor'].queryset = User.objects.filter(
            user_type='professor', 
            is_approved=True
        ).order_by('first_name', 'last_name')
        
        # Configurar limites de data - para exceções, permitir qualquer data futura
        today = timezone.now().date()
        # Permitir agendamentos a partir de hoje até 3 meses no futuro
        max_date = today + timedelta(days=90)
        
        self.fields['scheduled_date'].widget.attrs.update({
            'min': today.strftime('%Y-%m-%d'),
            'max': max_date.strftime('%Y-%m-%d'),
        })

    def clean_scheduled_date(self):
        date = self.cleaned_data.get('scheduled_date')
        if not date:
            raise forms.ValidationError("A data é obrigatória para agendamentos de exceção.")
        
        today = timezone.now().date()
        if date < today:
            raise forms.ValidationError("Não é possível agendar para datas passadas.")
        
        # Para exceções, permitir qualquer dia da semana
        return date

    def clean_exception_reason(self):
        reason = self.cleaned_data.get('exception_reason')
        if not reason or len(reason.strip()) < 10:
            raise forms.ValidationError("O motivo da exceção deve ter pelo menos 10 caracteres.")
        return reason.strip()

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        laboratory = cleaned_data.get('laboratory')
        scheduled_date = cleaned_data.get('scheduled_date')
        professor = cleaned_data.get('professor')
        number_of_students = cleaned_data.get('number_of_students')

        # Definir horários baseados no período para verificação de conflitos
        start_time = None
        end_time = None
        if period == 'matutino':
            start_time = time(7, 0)
            end_time = time(12, 0)
        elif period == 'noturno':
            start_time = time(19, 0)
            end_time = time(23, 0)

        # Verificar capacidade do laboratório
        if laboratory and number_of_students and hasattr(laboratory, 'capacity') and laboratory.capacity:
            if number_of_students > laboratory.capacity:
                self.add_error('number_of_students', 
                              f'O número de alunos ({number_of_students}) excede a capacidade do laboratório ({laboratory.capacity} pessoas).')

        # Verificar conflitos de horário com outros agendamentos aprovados
        if all([laboratory, scheduled_date, start_time, end_time]):
            conflicting_schedules = ScheduleRequest.objects.filter(
                laboratory=laboratory,
                scheduled_date=scheduled_date,
                status='approved'
            )
            
            if self.instance and self.instance.pk:
                conflicting_schedules = conflicting_schedules.exclude(pk=self.instance.pk)
            
            for schedule in conflicting_schedules:
                if (schedule.start_time <= start_time < schedule.end_time or
                    schedule.start_time < end_time <= schedule.end_time or
                    start_time <= schedule.start_time and end_time >= schedule.end_time):
                    self.add_error('period', 
                                  f'Conflito de horário com agendamento existente: {schedule.start_time} - {schedule.end_time}')
                    break

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Marcar como agendamento de exceção
        instance.is_exception = True
        instance.created_by_technician = self.technician
        instance.status = 'approved'  # Exceções são automaticamente aprovadas
        instance.reviewed_by = self.technician
        instance.review_date = timezone.now()
        
        if commit:
            instance.save()
        
        return instance

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