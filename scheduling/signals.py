# scheduling/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ScheduleRequest, DraftScheduleRequest


def invalidate_schedule_caches():
    """Invalida todos os caches relacionados a agendamentos"""
    cache_keys = [
        'pending_requests_list',
        'pending_appointments_count',
    ]
    cache.delete_many(cache_keys)


@receiver(post_save, sender=ScheduleRequest)
def schedule_request_saved(sender, instance, created, **kwargs):
    """Invalida cache quando uma solicitação é salva"""
    invalidate_schedule_caches()


@receiver(post_delete, sender=ScheduleRequest)
def schedule_request_deleted(sender, instance, **kwargs):
    """Invalida cache quando uma solicitação é deletada"""
    invalidate_schedule_caches()


@receiver(post_save, sender=DraftScheduleRequest)
def draft_schedule_request_saved(sender, instance, created, **kwargs):
    """Invalida cache quando um rascunho é salvo"""
    # Não precisa invalidar cache para rascunhos, pois não afetam as solicitações pendentes
    pass


@receiver(post_delete, sender=DraftScheduleRequest)
def draft_schedule_request_deleted(sender, instance, **kwargs):
    """Invalida cache quando um rascunho é deletado"""
    # Não precisa invalidar cache para rascunhos, pois não afetam as solicitações pendentes
    pass