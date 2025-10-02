# inventory/forms.py
from django import forms
from .models import Material, MaterialCategory
from .services import DoclingService
from django.conf import settings


docling_service = DoclingService() if getattr(settings, 'DOCLING_ENABLED', False) else None

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'category', 'description', 'quantity', 'minimum_stock', 'laboratory', 'expiration_date', 'batch_number', 'photo', 'invoice']
        labels = {
            'name': 'Nome do Material',
            'category': 'Categoria',
            'description': 'Descrição',
            'quantity': 'Quantidade',
            'minimum_stock': 'Estoque Mínimo',
            'laboratory': 'Laboratório',
            'expiration_date': 'Data de Validade',
            'batch_number': 'Número do Lote',
            'photo': 'Foto do Material',
            'invoice': 'Nota Fiscal'
        }
        help_texts = {
            'name': 'Digite o nome do material (ex: Microscópio, Papel A4, etc.)',
            'category': 'Selecione a categoria do material',
            'description': 'Descrição detalhada do material (opcional)',
            'quantity': 'Quantidade atual disponível em estoque',
            'minimum_stock': 'Quantidade mínima antes de emitir alertas de estoque baixo',
            'laboratory': 'Laboratório onde o material está localizado',
            'expiration_date': 'Data de validade (opcional)',
            'batch_number': 'Número do lote do produto (opcional)',
            'photo': 'Imagem do material (JPG, PNG) (opcional)',
            'invoice': 'Arquivo da nota fiscal (PDF ou imagem) (opcional)'
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
            'expiration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: LOTE-2024-001 (opcional)'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'invoice': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,image/*'
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

    def clean(self):
        cleaned_data = super().clean()
        expiration_date = cleaned_data.get('expiration_date')
        
        # Validar se a data de validade não é no passado (se informada)
        if expiration_date:
            from django.utils import timezone
            if expiration_date < timezone.now().date():
                raise forms.ValidationError({
                    'expiration_date': 'A data de validade não pode ser no passado.'
                })

        return cleaned_data

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