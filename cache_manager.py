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
                # Fallback: limpar manualmente as chaves conhecidas que correspondem ao padrão
                if 'pending_requests' in pattern:
                    keys_to_delete = [
                        'pending_requests_list',
                        'pending_appointments_count',
                    ]
                    # Adicionar chaves dinâmicas de usuários (limitar aos últimos 10 users ativos)
                    for user_id in range(1, 11):  # Assumindo IDs de usuário de 1 a 10
                        keys_to_delete.append(f'pending_requests_list_{user_id}')
                    
                    cache.delete_many(keys_to_delete)
                    logger.info(f"Cache invalidated manually for pattern: {pattern}")
                elif 'dashboard' in pattern:
                    keys_to_delete = [
                        'dashboard_stats_technician',
                        'dashboard_stats_professor',
                        'dash_dashboard_stats',
                        'dash_pending_requests',
                        'dash_pending_appointments'
                    ]
                    cache.delete_many(keys_to_delete)
                    logger.info(f"Dashboard cache invalidated manually for pattern: {pattern}")
                elif 'appointments' in pattern:
                    keys_to_delete = [
                        'dash_pending_appointments',
                        'pending_appointments_count'
                    ]
                    cache.delete_many(keys_to_delete)
                    logger.info(f"Appointments cache invalidated manually for pattern: {pattern}")
                else:
                    logger.debug(f"No manual invalidation rule for pattern: {pattern} (this is not an error)")
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
    
    @classmethod
    def force_invalidate_all_scheduling_cache(cls):
        """Força invalidação completa de todos os caches de agendamento"""
        # Lista completa de chaves de cache relacionadas a agendamentos
        cache_keys = [
            'pending_requests_list',
            'pending_appointments_count',
            'dashboard_stats_technician', 
            'dashboard_stats_professor',
            'dash_dashboard_stats',
            'dash_pending_requests',
            'sched_pending_requests',
            'dash_pending_appointments'
        ]
        
        # Adicionar chaves específicas de usuários (expandir conforme necessário)
        for user_id in range(1, 21):  # Suporte para usuários ID 1-20
            cache_keys.extend([
                f'pending_requests_list_{user_id}',
                f'sched_pending_requests_list_{user_id}',
                f'dash_dashboard_stats_technician_{user_id}',
                f'dash_dashboard_stats_professor_{user_id}'
            ])
        
        # Deletar todas as chaves
        cache.delete_many(cache_keys)
        logger.info(f"Force invalidated {len(cache_keys)} scheduling cache keys")
        
        # Também tentar invalidar por padrão se disponível
        cls.invalidate_pattern('pending_requests')
        cls.invalidate_pattern('dashboard')


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