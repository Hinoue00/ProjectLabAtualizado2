from django import forms
from .models import Laboratory, Department
from accounts.models import User

class LaboratoryForm(forms.ModelForm):
    """Formulário híbrido durante transição"""
    
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        required=True,
        label="Departamentos",
        help_text="Selecione um ou mais departamentos aos quais este laboratório pertence"
    )
    
    class Meta:
        model = Laboratory
        fields = [
            'name', 'location', 'capacity', 'departments',
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
        
        if self.instance and self.instance.pk:
            self.fields['departments'].initial = self.instance.departments.all()
    
    def clean_departments(self):
        departments = self.cleaned_data.get('departments')
        
        if not departments:
            raise forms.ValidationError('Selecione pelo menos um departamento.')
        
        return departments
    
    def save(self, commit=True):
        laboratory = super().save(commit=False)
        
        # 🔧 CORREÇÃO: Definir department como None para não dar erro
        laboratory.department = None
        
        if commit:
            laboratory.save()
            
            # Salvar departamentos
            laboratory.departments.clear()
            laboratory.departments.set(self.cleaned_data['departments'])
        
        return laboratory