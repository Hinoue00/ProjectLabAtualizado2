from django.contrib import admin
from .models import Laboratory, Department
from .forms import LaboratoryForm

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'color', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    form = LaboratoryForm
    
    list_display = ('name', 'get_departments_display', 'get_technicians_display', 'location', 'capacity', 'is_active')
    list_filter = ('departments', 'responsible_technicians', 'is_active', 'created_at')
    search_fields = ('name', 'location', 'description')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'location', 'capacity', 'is_active')
        }),
        ('Responsabilidade', {
            'fields': ('departments', 'responsible_technicians'),
            'description': 'Selecione os departamentos e técnicos responsáveis.'
        }),
        ('Detalhes', {
            'fields': ('description', 'equipment'),
            'classes': ('collapse',)
        }),
    )
    
    def get_departments_display(self, obj):
        return obj.get_departments_display()
    get_departments_display.short_description = 'Departamentos'
    
    def get_technicians_display(self, obj):
        return obj.get_technicians_display()
    get_technicians_display.short_description = 'Técnicos Responsáveis'