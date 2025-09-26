# cache_manager.py
"""
Sistema de cache inteligente com invalidação automática para LabConnect
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Gerenciador de cache com invalidação inteligente"""
    
    # Prefixos de cache por módulo
    CACHE_PREFIXES = {
        'dashboard': 'dash',
        'scheduling': 'sched',
        'inventory': 'inv',
        'materials': 'mat',
        'users': 'users'
    }
    
    # TTL padrão por tipo de dados
    CACHE_TTL = {
        'dashboard_stats': 600,      # 10 minutos
        'pending_requests': 120,     # 2 minutos
        'materials_stats': 600,      # 10 minutos
        'user_data': 3600,           # 1 hora
        'laboratory_data': 1800,     # 30 minutos
    }
    
    @classmethod
    def get_cache_key(cls, cache_type, *args):
        """Gera chave de cache padronizada"""
        prefix = cls.CACHE_PREFIXES.get(cache_type.split('_')[0], 'labconnect')
        key_parts = [prefix, cache_type] + [str(arg) for arg in args]
        return '_'.join(key_parts)
    
    @classmethod
    def set_cache(cls, cache_type, value, *args, ttl=None):
        """Define valor no cache com TTL apropriado"""
        key = cls.get_cache_key(cache_type, *args)
        if ttl is None:
            ttl = cls.CACHE_TTL.get(cache_type, 300)
        
        cache.set(key, value, ttl)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return key
    
    @classmethod
    def get_cache(cls, cache_type, *args):
        """Obtém valor do cache"""
        key = cls.get_cache_key(cache_type, *args)
        value = cache.get(key)
        logger.debug(f"Cache GET: {key} {'HIT' if value is not None else 'MISS'}")
        return value
    
    @classmethod
    def delete_cache(cls, cache_type, *args):
        """Remove item específico do cache"""
        key = cls.get_cache_key(cache_type, *args)
        cache.delete(key)
        logger.debug(f"Cache DELETE: {key}")
    
    @classmethod
    def invalidate_pattern(cls, pattern):
        """Invalida todas as chaves que correspondem a um padrão"""
        # Para Redis: usar delete_pattern
        # Para outros backends: implementar busca manual
        try:
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(f"*{pattern}*")
                logger.info(f"Cache invalidated pattern: {pattern}")
            else:
                # Fallback para backends sem delete_pattern
                logger.warning(f"Pattern invalidation not supported for cache backend")
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
    
    @classmethod
    def invalidate_dashboard_cache(cls, user_type=None, department=None):
        """Invalida cache do dashboard"""
        patterns = ['dash_dashboard_stats', 'dash_pending_requests']
        
        if user_type:
            patterns.append(f'dash_dashboard_stats_{user_type}')
        if department:
            patterns.append(f'dash_dashboard_stats_{department}')
            patterns.append(f'mat_materials_stats_{department}')
        
        for pattern in patterns:
            cls.invalidate_pattern(pattern)
    
    @classmethod
    def invalidate_scheduling_cache(cls, user_id=None):
        """Invalida cache de agendamentos"""
        patterns = ['sched_pending_requests', 'dash_pending_appointments']
        
        if user_id:
            patterns.append(f'sched_pending_requests_list_{user_id}')
        
        for pattern in patterns:
            cls.invalidate_pattern(pattern)
    
    @classmethod
    def invalidate_materials_cache(cls, department=None, laboratory_id=None):
        """Invalida cache de materiais"""
        patterns = ['mat_materials_stats', 'inv_materials_list']
        
        if department:
            patterns.append(f'mat_materials_stats_{department}')
        if laboratory_id:
            patterns.append(f'inv_materials_lab_{laboratory_id}')
        
        for pattern in patterns:
            cls.invalidate_pattern(pattern)


# === SIGNALS PARA INVALIDAÇÃO AUTOMÁTICA ===

@receiver(post_save, sender='scheduling.ScheduleRequest')
def invalidate_schedule_cache(sender, instance, **kwargs):
    """Invalida cache quando agendamento é modificado"""
    CacheManager.invalidate_scheduling_cache()
    CacheManager.invalidate_dashboard_cache()
    logger.info(f"Cache invalidated due to ScheduleRequest change: {instance.id}")

@receiver(post_delete, sender='scheduling.ScheduleRequest')
def invalidate_schedule_cache_delete(sender, instance, **kwargs):
    """Invalida cache quando agendamento é deletado"""
    CacheManager.invalidate_scheduling_cache()
    CacheManager.invalidate_dashboard_cache()
    logger.info(f"Cache invalidated due to ScheduleRequest deletion: {instance.id}")

@receiver(post_save, sender='inventory.Material')
def invalidate_material_cache(sender, instance, **kwargs):
    """Invalida cache quando material é modificado"""
    department = None
    if instance.laboratory and hasattr(instance.laboratory, 'departments'):
        dept_codes = instance.laboratory.get_departments_codes()
        department = dept_codes[0] if dept_codes else None
    
    CacheManager.invalidate_materials_cache(department, instance.laboratory_id)
    CacheManager.invalidate_dashboard_cache(department=department)
    logger.info(f"Cache invalidated due to Material change: {instance.id}")

@receiver(post_delete, sender='inventory.Material')
def invalidate_material_cache_delete(sender, instance, **kwargs):
    """Invalida cache quando material é deletado"""
    CacheManager.invalidate_materials_cache()
    CacheManager.invalidate_dashboard_cache()
    logger.info(f"Cache invalidated due to Material deletion: {instance.id}")

@receiver(post_save, sender='scheduling.ScheduleRequestComment')
def invalidate_comment_cache(sender, instance, **kwargs):
    """Invalida cache quando comentário é adicionado"""
    CacheManager.invalidate_scheduling_cache(instance.schedule_request.professor_id)
    logger.info(f"Cache invalidated due to Comment change: {instance.id}")

@receiver(post_save, sender='accounts.User')
def invalidate_user_cache(sender, instance, **kwargs):
    """Invalida cache quando usuário é modificado"""
    if instance.user_type == 'professor':
        CacheManager.invalidate_scheduling_cache(instance.id)
    
    if instance.is_approved:
        CacheManager.invalidate_dashboard_cache()
    
    logger.info(f"Cache invalidated due to User change: {instance.id}")

# === DECORATORS PARA CACHE ===

def cache_result(cache_type, timeout=None):
    """Decorator para cachear resultado de função"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Gerar chave baseada em argumentos
            cache_key = CacheManager.get_cache_key(cache_type, str(hash(str(args) + str(kwargs))))
            
            # Tentar obter do cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT for {func.__name__}: {cache_key}")
                return result
            
            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            ttl = timeout or CacheManager.CACHE_TTL.get(cache_type, 300)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache SET for {func.__name__}: {cache_key} (TTL: {ttl}s)")
            
            return result
        return wrapper
    return decorator