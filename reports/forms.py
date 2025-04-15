# reports/forms.py
from django import forms
from .models import Report
from laboratories.models import Laboratory
from django.utils import timezone
from datetime import timedelta

class ReportFilterForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=Report.REPORT_TYPES,
        label='Tipo de Relatório',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range_start = forms.DateField(
        label='Data Inicial',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date() - timedelta(days=30)
    )
    
    date_range_end = forms.DateField(
        label='Data Final',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )
    
    laboratory = forms.ModelChoiceField(
        queryset=Laboratory.objects.all(),
        label='Laboratório',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_charts = forms.BooleanField(
        label='Incluir Gráficos',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    export_format = forms.ChoiceField(
        choices=[('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')],
        label='Formato de Exportação',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_range_start = cleaned_data.get('date_range_start')
        date_range_end = cleaned_data.get('date_range_end')
        
        if date_range_start and date_range_end and date_range_start > date_range_end:
            raise forms.ValidationError('A data inicial não pode ser posterior à data final.')
        
        return cleaned_data
