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
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # Adicionar também um campo para criação
    updated_at = models.DateTimeField(auto_now=True, null=True)  # Campo que está faltando

    
    def __str__(self):
        return f"{self.name} ({self.quantity} units)"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock
    
    @property
    def stock_percentage(self):
        if self.minimum_stock == 0:
            return 100
        return min((self.quantity / self.minimum_stock) * 100, 100)
    
    analyzed_data = models.JSONField(null=True, blank=True, 
                                    help_text="Dados da análise por NLP")
    suggested_category = models.CharField(max_length=50, blank=True, null=True, default="",
                                        help_text="Categoria sugerida pelo sistema")
    
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
                models.Index(fields=['quantity']),  # Para consultas de estoque baixo
            ]   