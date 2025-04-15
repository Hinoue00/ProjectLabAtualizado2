# scheduling/forms.py
from django import forms
from .models import ScheduleRequest, Laboratory, User
from django.utils import timezone
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from datetime import datetime, timedelta, time
from django.core.validators import FileExtensionValidator

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
    
    class Meta:
        model = ScheduleRequest
        fields = [
            'laboratory', 'subject', 'description', 
            'scheduled_date', 'shift',  # Substituímos start_time e end_time por shift 
            'number_of_students', 'materials',
            'guide_file',
        ]
        widgets = {
            'scheduled_date': DateInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
            'materials': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Liste os materiais necessários para a aula...'}),
        }

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas laboratórios ativos
        self.fields['laboratory'].queryset = Laboratory.objects.filter(is_active=True)
        
        # Adiciona classes Bootstrap aos campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Aplica limites de data (próxima semana)
        today = timezone.now().date()
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=4)

        # Configurar o campo de data para não permitir fins de semana
        self.fields['scheduled_date'].widget.attrs.update({
            'min': next_week_start,
            'max': next_week_end,
        })

        # Se estamos editando um agendamento existente, preencher o campo de turno
        instance = kwargs.get('instance')
        if instance and hasattr(instance, 'start_time') and hasattr(instance, 'end_time'):
            if instance.start_time:
                start_hour = instance.start_time.hour
                if 7 <= start_hour < 12:
                    self.initial['shift'] = 'morning'
                elif 12 <= start_hour < 18:
                    self.initial['shift'] = 'afternoon'
                else:
                    self.initial['shift'] = 'evening'

    def clean_scheduled_date(self):
        """Valida que a data é em um dia de semana (segunda a sexta)"""
        date = self.cleaned_data.get('scheduled_date')
        
        if date:
            if date.weekday() > 4:  # 5=sábado, 6=domingo
                raise forms.ValidationError("Por favor, selecione apenas dias úteis (segunda a sexta).")
                
            # Valida que a data está na próxima semana
            today = timezone.now().date()
            next_week_start = today + timedelta(days=(7 - today.weekday()))
            next_week_end = next_week_start + timedelta(days=4)  # Segunda a sexta
            
            if not (next_week_start <= date <= next_week_end):
                raise forms.ValidationError("Os agendamentos só podem ser realizados para a próxima semana.")
        
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
    """Formulário para atualização de perfil do usuário"""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'lab_department')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Torna o campo lab_department opcional (só para técnicos)
        self.fields['lab_department'].required = False
        
        # Adiciona classes Bootstrap aos campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        """Verifica se o email já está em uso por outro usuário"""
        email = self.cleaned_data.get('email')
        
        # Se o email foi alterado, verifica se já existe
        if email and email != self.instance.email:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('Este email já está em uso.')
        
        return email

class PasswordChangeForm(DjangoPasswordChangeForm):
    """Formulário para alteração de senha"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Adiciona classes Bootstrap aos campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'