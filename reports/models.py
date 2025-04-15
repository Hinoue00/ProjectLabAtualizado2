# reports/models.py
from django.db import models
from django.utils import timezone
from accounts.models import User

class Report(models.Model):
    REPORT_TYPES = (
        ('scheduling', 'Agendamentos'),
        ('inventory', 'Inventário'),
        ('user_activity', 'Atividade dos Usuários'),
    )
    
    title = models.CharField(max_length=100)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    filter_params = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"
