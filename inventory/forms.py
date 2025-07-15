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
        labels = {
            'name': 'Nome do Material',
            'category': 'Categoria',
            'description': 'Descrição',
            'quantity': 'Quantidade',
            'minimum_stock': 'Estoque Mínimo',
            'laboratory': 'Laboratório'
        }
        help_texts = {
            'name': 'Digite o nome do material (ex: Microscópio, Papel A4, etc.)',
            'category': 'Selecione a categoria do material',
            'description': 'Descrição detalhada do material (opcional)',
            'quantity': 'Quantidade atual disponível em estoque',
            'minimum_stock': 'Quantidade mínima antes de emitir alertas de estoque baixo',
            'laboratory': 'Laboratório onde o material está localizado'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Microscópio Óptico'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição detalhada do material...'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': '0'
            }),
            'minimum_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '1'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Adicionar classe para previsão em tempo real
        if docling_service:
            self.fields['description'].widget.attrs.update({
                'class': 'form-control docling-analyze',
                'data-target': 'category'
            })
        
        # Personalizar o campo de categoria
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['laboratory'].widget.attrs.update({'class': 'form-select'})
        
        # Adicionar texto de ajuda personalizado
        self.fields['category'].empty_label = "Selecione uma categoria"
        self.fields['laboratory'].empty_label = "Selecione um laboratório"

class MaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = MaterialCategory
        fields = ['name', 'material_type']
        labels = {
            'name': 'Nome da Categoria',
            'material_type': 'Tipo de Material'
        }
        help_texts = {
            'name': 'Digite o nome da categoria (ex: Química, Eletrônicos, Vidraria)',
            'material_type': 'Selecione o tipo de material desta categoria'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Equipamentos de Laboratório'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

class ImportMaterialsForm(forms.Form):
    file = forms.FileField(
        label='Selecionar arquivo Excel ou CSV',
        help_text='O arquivo deve conter as colunas: nome, categoria, descrição, quantidade, estoque_mínimo, laboratório',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            if not (file.name.endswith('.csv') or file.name.endswith('.xlsx') or file.name.endswith('.xls')):
                raise forms.ValidationError('O arquivo deve estar em formato CSV ou Excel')
            
            # Verificar tamanho do arquivo (máximo 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('O arquivo não pode ser maior que 10MB')
        
        return file