# scheduling/models.py
from datetime import datetime, time
from django.db import models
from accounts.models import User
from django.utils import timezone
from laboratories.models import Laboratory
from django.core.validators import FileExtensionValidator

class ScheduleRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pendente'),
        ('approved', 'Aprovado'),
        ('rejected', 'Rejeitado'),
    )
    
    professor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'professor'})
    laboratory = models.ForeignKey(Laboratory, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, verbose_name="Assunto/Disciplina")
    description = models.TextField(verbose_name="Descrição da atividade", blank=True, null=True)
    scheduled_date = models.DateField(verbose_name="Data agendada")
    start_time = models.TimeField(verbose_name="Hora de início")
    end_time = models.TimeField(verbose_name="Hora de término")
    number_of_students = models.IntegerField(verbose_name="Número de alunos", null=True, blank=True)
    class_semester = models.CharField(max_length=50, verbose_name="Semestre/Turma", blank=True, null=True)
    materials = models.TextField(verbose_name="Materiais necessários", blank=True, null=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    review_date = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_requests',
        limit_choices_to={'user_type': 'technician'}
    )
    rejection_reason = models.TextField(blank=True, null=True)

    guide_file = models.FileField(
        upload_to='lab_guides/',
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'odt'])],
        verbose_name="Roteiro de Aula"
    )
    
    class Meta:
        verbose_name = "Solicitação de Agendamento"
        verbose_name_plural = "Solicitações de Agendamento"
        ordering = ['-scheduled_date', 'start_time']
        indexes = [
            models.Index(fields=['status'], name='scheduling_status_idx'),
            models.Index(fields=['status', '-request_date'], name='scheduling_status_date_idx'),
            models.Index(fields=['professor', 'status'], name='scheduling_prof_status_idx'),
            models.Index(fields=['laboratory', 'scheduled_date', 'status'], name='scheduling_lab_date_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.professor.get_full_name()} - {self.laboratory.name} - {self.scheduled_date}"
    
    @property
    def duration(self):
        """Calcula a duração da reserva em horas"""
        if not self.start_time or not self.end_time:
            return 0
            
        # Convertendo para datetime para facilitar o cálculo
        start_dt = timezone.make_aware(timezone.datetime.combine(timezone.now().date(), self.start_time))
        end_dt = timezone.make_aware(timezone.datetime.combine(timezone.now().date(), self.end_time))
        
        # Se end_time for menor que start_time, assumimos que é no dia seguinte
        if end_dt < start_dt:
            end_dt = end_dt + timezone.timedelta(days=1)
        
        # Calcula a diferença em horas
        duration = (end_dt - start_dt).total_seconds() / 3600
        return round(duration, 1)
    
    def approve(self, reviewer):
        """Aprova a solicitação de agendamento"""
        self.status = 'approved'
        self.review_date = timezone.now()
        self.reviewed_by = reviewer
        self.save()
    
    def reject(self, reviewer, reason=None):
        """Rejeita a solicitação de agendamento"""
        self.status = 'rejected'
        self.review_date = timezone.now()
        self.reviewed_by = reviewer
        if reason:
            self.rejection_reason = reason
        self.save()
    
    def is_conflicting(self):
        """Verifica se há conflito de horário com outros agendamentos aprovados"""
        # Busca agendamentos no mesmo laboratório, na mesma data, com status aprovado
        conflicting_schedules = ScheduleRequest.objects.filter(
            laboratory=self.laboratory,
            scheduled_date=self.scheduled_date,
            status='approved'
        ).exclude(id=self.id)
        
        # Verifica se há sobreposição de horários
        for schedule in conflicting_schedules:
            # Se o início da nova reserva está dentro do período de uma existente
            if schedule.start_time <= self.start_time < schedule.end_time:
                return True
            # Se o término da nova reserva está dentro do período de uma existente
            if schedule.start_time < self.end_time <= schedule.end_time:
                return True
            # Se a nova reserva engloba completamente uma existente
            if self.start_time <= schedule.start_time and self.end_time >= schedule.end_time:
                return True
        
        return False
    
    def can_be_requested(self):
        """Verifica se a solicitação atende aos requisitos (dia e semana)"""
        today = timezone.now().date()
        
        # Só pode solicitar às quintas e sextas
        if today.weekday() not in [3, 4]:  # 3=quinta, 4=sexta
            return False, "Agendamentos só podem ser solicitados às quintas e sextas-feiras."
        
        # Só pode solicitar para a próxima semana
        next_week_start = today + timezone.timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timezone.timedelta(days=6)
        
        if not (next_week_start <= self.scheduled_date <= next_week_end):
            return False, "Agendamentos só podem ser feitos para a próxima semana."
        
        return True, ""
    
    def save(self, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        # Log detalhado para debug
        if not self.pk:  # Nova criação
            logger.info(f"🟢 CRIANDO NOVO AGENDAMENTO:")
            logger.info(f"   Professor: {self.professor.get_full_name()} (ID: {self.professor.id})")
            logger.info(f"   Laboratório: {self.laboratory.name} (ID: {self.laboratory.id})")
            logger.info(f"   Departamento Lab: {self.laboratory.department}")
            logger.info(f"   Data: {self.scheduled_date}")
            logger.info(f"   Horário: {self.start_time} - {self.end_time}")
            logger.info(f"   Status: {self.status}")
            logger.info(f"   Disciplina: {self.subject}")
        else:
            logger.info(f"🔄 ATUALIZANDO AGENDAMENTO ID {self.pk}")
            logger.info(f"   Status: {self.status}")
        
        # Salvar normalmente
        super().save(*args, **kwargs)
        
        # Log após salvar
        logger.info(f"✅ AGENDAMENTO SALVO COM SUCESSO - ID: {self.pk}")
        
        # Debug adicional para verificar se está sendo salvo no DB
        try:
            saved_obj = ScheduleRequest.objects.get(pk=self.pk)
            logger.info(f"✅ CONFIRMADO NO DB - ID: {saved_obj.pk}, Status: {saved_obj.status}")
        except ScheduleRequest.DoesNotExist:
            logger.error(f"❌ ERRO: Agendamento não encontrado no DB após salvar!")

    
# Adicione no arquivo scheduling/models.py

class DraftScheduleRequest(models.Model):
    """
    Modelo para rascunhos de agendamentos antes da confirmação
    """
    professor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'user_type': 'professor'}
    )
    laboratory = models.ForeignKey(Laboratory, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, verbose_name="Assunto/Disciplina")
    description = models.TextField(verbose_name="Descrição da atividade", blank=True, null=True)
    scheduled_date = models.DateField(verbose_name="Data agendada")
    start_time = models.TimeField(verbose_name="Hora de início", null=True, blank=True)
    end_time = models.TimeField(verbose_name="Hora de término", null=True, blank=True)
    number_of_students = models.IntegerField(
        verbose_name="Número de alunos", 
        null=True, 
        blank=True
    )
    class_semester = models.CharField(
        max_length=50, 
        verbose_name="Semestre/Turma", 
        blank=True, 
        null=True
    )
    materials = models.TextField(
        verbose_name="Materiais necessários", 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    SHIFT_CHOICES = (
        ('morning', 'Matutino (08:00 - 12:00)'),
        ('evening', 'Noturno (19:00 - 22:00)'),
    )

    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='evening')

    guide_file = models.FileField(
        upload_to='lab_guides/',
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'odt'])],
        verbose_name="Roteiro de Aula"
    )

    class Meta:
        verbose_name = "Rascunho de Agendamento"
        verbose_name_plural = "Rascunhos de Agendamentos"
        ordering = ['-created_at']

    def __str__(self):
        return f"Rascunho: {self.subject} - {self.scheduled_date}"
    
     # Métodos para converter entre turno e horários concretos
    def set_times_from_shift(self):
        """Define os horários com base no turno selecionado"""
        if self.shift == 'morning':
            self.start_time = time(8, 0)
            self.end_time = time(12, 0)
        elif self.shift == 'evening':
            self.start_time = time(19, 0)
            self.end_time = time(22, 0)
    
    def get_shift_from_times(self):
        """Determina o turno com base nos horários definidos"""
        if not self.start_time:
            return 'morning'
            
        start_hour = self.start_time.hour
        if 7 <= start_hour < 12:
            return 'morning'
        elif 19 <= start_hour < 22:
            return 'evening'
        
class FileAttachment(models.Model):
    """Model to store files attached to schedule requests"""
    schedule_request = models.ForeignKey(
        ScheduleRequest, 
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='schedule_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.file_name
    
    def get_file_extension(self):
        return self.file_name.split('.')[-1].lower()
    
    @property
    def is_image(self):
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
        return self.get_file_extension() in image_extensions
    
    @property
    def is_pdf(self):
        return self.get_file_extension() == 'pdf'
    
    @property
    def is_document(self):
        doc_extensions = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt']
        return self.get_file_extension() in doc_extensions