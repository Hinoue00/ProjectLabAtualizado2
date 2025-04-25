# laboratories/forms.py
from django import forms
from .models import Laboratory
from accounts.models import User

class LaboratoryForm(forms.ModelForm):
    class Meta:
        model = Laboratory
        fields = ['name', 'location', 'capacity', 'description', 'responsible_technician', 'department']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show technicians in the dropdown
        self.fields['responsible_technician'].queryset = User.objects.filter(
            user_type='technician',
            is_approved=True
        )
