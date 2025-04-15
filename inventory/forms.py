# inventory/forms.py
from django import forms
from .models import Material, MaterialCategory
import pandas as pd
from .services import DoclingService
from django.conf import settings


docling_service = DoclingService() if getattr(settings, 'DOCLING_ENABLED', False) else None

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'category', 'description', 'quantity', 'minimum_stock', 'laboratory']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Adicionar classe para previsão em tempo real
        if docling_service:
            self.fields['description'].widget.attrs.update({
                'class': 'form-control docling-analyze',
                'data-target': 'category'
            })

class MaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = MaterialCategory
        fields = ['name', 'material_type']

class ImportMaterialsForm(forms.Form):
    file = forms.FileField(
        label='Select Excel or CSV file',
        help_text='The file should have columns: name, category, description, quantity, minimum_stock, laboratory'
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            if not (file.name.endswith('.csv') or file.name.endswith('.xlsx') or file.name.endswith('.xls')):
                raise forms.ValidationError('File must be CSV or Excel format')
        
        return file