from django.db import models
from accounts.models import User
from django.utils import timezone

class Department(models.Model):
    """Modelo para departamentos"""
    code = models.CharField(
        max_length=20, 
        unique=True,
        verbose_name="Código"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Nome"
    )
    description = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Descrição"
    )
    color = models.CharField(
        max_length=7, 
        default="#007bff",
        help_text="Cor em hexadecimal (ex: #007bff)",
        verbose_name="Cor"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Laboratory(models.Model):
    # Campos básicos
    name = models.CharField(max_length=100, verbose_name="Nome")
    location = models.CharField(max_length=100, verbose_name="Localização")
    capacity = models.PositiveIntegerField(verbose_name="Capacidade")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Campo para indicar se é um laboratório de estoque/armazenamento
    is_storage = models.BooleanField(
        default=False, 
        verbose_name="Estoque/Armazenamento", 
        help_text="Marque se este laboratório é usado apenas para armazenar materiais (não disponível para agendamento)"
    )
    
    # 🔧 MANTER CAMPO ANTIGO (transitório)
    DEPARTMENT_CHOICES = (
        ('exatas', 'Exatas'),
        ('saude', 'Saúde'),
        ('informatica', 'Informática'),
    )
    
    department = models.CharField(
        max_length=100, 
        choices=DEPARTMENT_CHOICES,
        verbose_name="Departamento (Antigo)",
        help_text="Este campo será substituído em breve",
        blank=True,
        null=True
    )
    
    # Departamentos múltiplos
    departments = models.ManyToManyField(
        Department,
        verbose_name="Departamentos",
        help_text="Selecione os departamentos aos quais este laboratório pertence",
        blank=True
    )
    
    # 🔧 MANTER CAMPO ANTIGO DE TÉCNICO (transitório)
    responsible_technician = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        limit_choices_to={'user_type': 'technician'},
        verbose_name="Técnico Responsável (Antigo)",
        help_text="Este campo será substituído em breve"
    )
    
    # 🔧 NOVO: Múltiplos técnicos responsáveis
    responsible_technicians = models.ManyToManyField(
        User,
        limit_choices_to={'user_type': 'technician', 'is_approved': True},
        verbose_name="Técnicos Responsáveis",
        help_text="Selecione os técnicos responsáveis por este laboratório",
        blank=True,
        related_name='managed_laboratories'
    )
    
    equipment = models.TextField(blank=True, null=True, verbose_name="Equipamentos")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Laboratório"
        verbose_name_plural = "Laboratórios"
        ordering = ['name']
    
    def __str__(self):
        dept_names = self.get_departments_display()
        storage_suffix = " [ESTOQUE]" if self.is_storage else ""
        return f"{self.name} ({dept_names}){storage_suffix}"
    
    def get_departments_display(self):
        """Retorna string com nomes dos departamentos"""
        if self.departments.exists():
            return ", ".join([dept.name for dept in self.departments.all()])
        elif self.department:
            return self.get_department_display()
        else:
            return "Sem departamento"
    
    def get_departments_codes(self):
        """Retorna lista com códigos dos departamentos"""
        if self.departments.exists():
            return [dept.code for dept in self.departments.all()]
        elif self.department:
            return [self.department]
        else:
            return []
    
    def belongs_to_department(self, department_code):
        """Verifica se o laboratório pertence ao departamento"""
        if self.departments.filter(code=department_code).exists():
            return True
        return self.department == department_code
    
    # 🔧 NOVOS MÉTODOS PARA TÉCNICOS
    def get_technicians_display(self):
        """Retorna string com nomes dos técnicos responsáveis"""
        if self.responsible_technicians.exists():
            return ", ".join([tech.get_full_name() for tech in self.responsible_technicians.all()])
        elif self.responsible_technician:
            return self.responsible_technician.get_full_name()
        else:
            return "Sem técnico responsável"
    
    def get_technicians_list(self):
        """Retorna lista de técnicos responsáveis"""
        if self.responsible_technicians.exists():
            return list(self.responsible_technicians.all())
        elif self.responsible_technician:
            return [self.responsible_technician]
        else:
            return []
    
    def has_technician(self, technician):
        """Verifica se um técnico é responsável por este laboratório"""
        if self.responsible_technicians.filter(id=technician.id).exists():
            return True
        return self.responsible_technician == technician
    
    def get_upcoming_schedules(self):
        today = timezone.now().date()
        return self.schedulerequest_set.filter(
            scheduled_date__gte=today,
            status='approved'
        ).order_by('scheduled_date', 'start_time')