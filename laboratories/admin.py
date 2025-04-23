# laboratories/admin.py
from django.contrib import admin
from .models import Laboratory

@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_department_display', 'location', 'capacity', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('name', 'location')
    
    def get_department_display(self, obj):
        """
        Retorna o nome amigável do departamento conforme definido em DEPARTMENT_CHOICES
        """
        return obj.get_department_display()
    
    get_department_display.short_description = 'Departamento'