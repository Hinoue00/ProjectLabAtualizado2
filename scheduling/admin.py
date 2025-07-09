from django.contrib import admin
from .models import ScheduleRequest, Laboratory, DraftScheduleRequest
import logging

logger = logging.getLogger(__name__)

@admin.register(ScheduleRequest)
class ScheduleRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'professor_name', 
        'laboratory_name', 
        'laboratory_department',
        'scheduled_date', 
        'start_time', 
        'end_time',
        'subject',
        'status', 
        'request_date'
    ]
    list_filter = [
        'status', 
        'laboratory__department',
        'laboratory',
        'scheduled_date',
        'request_date'
    ]
    search_fields = [
        'professor__first_name',
        'professor__last_name',
        'professor__email',
        'laboratory__name',
        'subject'
    ]
    ordering = ['-request_date']
    readonly_fields = ['request_date', 'review_date']
    
    def professor_name(self, obj):
        return obj.professor.get_full_name()
    professor_name.short_description = 'Professor'
    
    def laboratory_name(self, obj):
        return obj.laboratory.name
    laboratory_name.short_description = 'Laboratório'
    
    def laboratory_department(self, obj):
        return obj.laboratory.department
    laboratory_department.short_description = 'Departamento'
    
    def save_model(self, request, obj, form, change):
        if change:
            logger.info(f"🔧 ADMIN: Editando agendamento ID {obj.pk}")
        else:
            logger.info(f"🆕 ADMIN: Criando novo agendamento")
        
        logger.info(f"   Professor: {obj.professor.get_full_name()}")
        logger.info(f"   Laboratório: {obj.laboratory.name} ({obj.laboratory.department})")
        logger.info(f"   Status: {obj.status}")
        
        super().save_model(request, obj, form, change)

# Register your models here.
