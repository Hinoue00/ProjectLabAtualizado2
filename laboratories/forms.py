from django import forms
from .models import Laboratory, Department
from accounts.models import User

class LaboratoryForm(forms.ModelForm):
    """Formulário completo com departamentos e técnicos"""
    
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        required=True,
        label="Departamentos",
        help_text="Selecione um ou mais departamentos aos quais este laboratório pertence"
    )
    
    responsible_technicians = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            user_type='technician', 
            is_approved=True, 
            is_active=True
        ),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        required=False,  # Opcional
        label="Técnicos Responsáveis",
        help_text="Selecione os técnicos responsáveis por este laboratório (opcional)"
    )
    
    class Meta:
        model = Laboratory
        fields = [
            'name', 'location', 'capacity', 'departments',
            'responsible_technicians',  # 🔧 ADICIONADO!
            'description', 'equipment', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Laboratório de Física'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Bloco A - Sala 101'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Ex: 30'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do laboratório...'
            }),
            'equipment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Liste os equipamentos disponíveis...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar valores iniciais se editando um laboratório existente
        if self.instance and self.instance.pk:
            self.fields['departments'].initial = self.instance.departments.all()
            self.fields['responsible_technicians'].initial = self.instance.responsible_technicians.all()
    
    def clean_departments(self):
        departments = self.cleaned_data.get('departments')
        
        if not departments:
            raise forms.ValidationError('Selecione pelo menos um departamento.')
        
        return departments
    
    def save(self, commit=True):
        laboratory = super().save(commit=False)
        
        # 🔧 CORREÇÃO: Definir department como None para evitar erro de NOT NULL
        laboratory.department = None
        
        if commit:
            laboratory.save()
            
            # Salvar departamentos múltiplos
            laboratory.departments.clear()
            laboratory.departments.set(self.cleaned_data['departments'])
            
            # 🔧 NOVO: Salvar técnicos responsáveis
            laboratory.responsible_technicians.clear()
            if self.cleaned_data.get('responsible_technicians'):
                laboratory.responsible_technicians.set(self.cleaned_data['responsible_technicians'])
        
        return laboratory