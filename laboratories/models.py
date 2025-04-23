# laboratories/models.py
from django.db import models
from accounts.models import User
from django.utils import timezone

class Laboratory(models.Model):

    DEPARTMENT_CHOICES = (
    ('exatas', 'Exatas'),
    ('saude', 'Saúde'),
    ('informatica', 'Informática'),
    )
        
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    department = models.CharField(
        max_length=100, 
        choices=DEPARTMENT_CHOICES,
        verbose_name="Departamento"
    )
    equipment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Mantenha também o campo responsible_technician que já existia
    responsible_technician = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'technician'}
    )
    
    class Meta:
        verbose_name = "Laboratório"
        verbose_name_plural = "Laboratórios"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.department})"
    
    def get_upcoming_schedules(self):
        today = timezone.now().date()
        return self.schedulerequest_set.filter(
            scheduled_date__gte=today,
            status='approved'
        ).order_by('scheduled_date', 'start_time')