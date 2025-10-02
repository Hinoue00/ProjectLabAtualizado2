# inventory/models.py
from django.db import models
from laboratories.models import Laboratory
from .services import DoclingService
from django.conf import settings
import json
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

docling_service = DoclingService() if getattr(settings, 'DOCLING_ENABLED', False) else None

class MaterialCategory(models.Model):
    CATEGORY_TYPES = (
        ('consumable', 'Consumível'),
        ('permanent', 'Permanente'),
        ('perishable', 'Perecível'),
    )
    
    name = models.CharField(max_length=100)
    material_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    
    def __str__(self):
        return f"{self.name} ({self.get_material_type_display()})"
    
    class Meta:
        verbose_name_plural = "Material Categories"

class Material(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(MaterialCategory, on_delete=models.CASCADE)
    description = models.TextField()
    quantity = models.PositiveIntegerField()
    minimum_stock = models.PositiveIntegerField(help_text="Minimum quantity before alert")
    laboratory = models.ForeignKey(Laboratory, on_delete=models.CASCADE, related_name='materials')
    analyzed_data = models.JSONField(null=True, blank=True, help_text="Dados da análise por NLP")
    suggested_category = models.CharField(max_length=50, blank=True, help_text="Categoria sugerida pelo sistema")
    
    # Campos de validade (opcionais para todos os tipos)
    expiration_date = models.DateField(null=True, blank=True, verbose_name="Data de Validade", help_text="Data de vencimento do material (opcional)")
    batch_number = models.CharField(max_length=50, blank=True, verbose_name="Número do Lote", help_text="Identificação do lote (opcional)")

    # Campos de documentação e imagem
    invoice = models.FileField(upload_to='invoices/', null=True, blank=True, verbose_name="Nota Fiscal", help_text="Arquivo da nota fiscal do material (PDF ou imagem)")
    photo = models.ImageField(upload_to='materials/', null=True, blank=True, verbose_name="Foto do Material", help_text="Imagem do material")

    created_at = models.DateTimeField(auto_now_add=True, null=True)  # Adicionar também um campo para criação
    updated_at = models.DateTimeField(auto_now=True, null=True)  # Campo que está faltando

    
    def __str__(self):
        return f"{self.name} ({self.quantity} units)"
    
    @property
    def is_low_stock(self):
        return self.quantity < self.minimum_stock
    
    @property
    def stock_percentage(self):
        if self.minimum_stock == 0:
            return 100
        return min((self.quantity / self.minimum_stock) * 100, 100)
    
    @property
    def is_expired(self):
        """Verifica se o material está vencido"""
        if not self.expiration_date:
            return False
        from django.utils import timezone
        return self.expiration_date < timezone.now().date()
    
    @property
    def days_to_expiration(self):
        """Retorna quantos dias restam até o vencimento"""
        if not self.expiration_date:
            return None
        from django.utils import timezone
        delta = self.expiration_date - timezone.now().date()
        return delta.days
    
    @property
    def is_near_expiration(self):
        """Verifica se o material está próximo do vencimento (3 meses)"""
        if not self.expiration_date:
            return False
        days_remaining = self.days_to_expiration
        return days_remaining is not None and 0 <= days_remaining <= 90  # 3 meses = ~90 dias
    
    @property
    def expiration_status(self):
        """Retorna status da validade: 'expired', 'near_expiration', 'valid', 'no_expiration'"""
        if not self.expiration_date:
            return 'no_expiration'
        
        if self.is_expired:
            return 'expired'
        elif self.is_near_expiration:
            return 'near_expiration'
        else:
            return 'valid'
    
    @property
    def requires_expiration_date(self):
        """Verifica se o material requer data de validade"""
        return self.category.material_type in ['consumable', 'perishable']
    
    
    def save(self, *args, **kwargs):
        # Usar docling para analisar descrição e sugerir categoria
        if docling_service and not self.id:  # Apenas para novos objetos
            # Analisar a descrição
            if self.description:
                self.analyzed_data = docling_service.analyze_text(self.description)
                
                # Sugerir categoria se não for especificada
                if not self.category_id:
                    suggested = docling_service.categorize_material(self.description)
                    self.suggested_category = suggested
                    
                    # Tentar encontrar uma categoria correspondente
                    try:
                        category = MaterialCategory.objects.filter(
                            material_type=suggested
                        ).first()
                        if category:
                            self.category = category
                    except:
                        pass
        
        super().save(*args, **kwargs)
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['laboratory']),
            models.Index(fields=['quantity', 'minimum_stock']),  # Para consultas de estoque baixo
            models.Index(fields=['laboratory', 'category']),  # Para filtros por lab e categoria
            models.Index(fields=['expiration_date'], condition=models.Q(expiration_date__isnull=False), name='material_expiration_idx'),  # Para materiais com validade
            models.Index(fields=['created_at']),  # Para ordenação temporal
            models.Index(fields=['laboratory', 'quantity']),  # Para dashboard de materiais por lab
        ]   