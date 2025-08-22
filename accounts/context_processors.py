# accounts/context_processors.py
from scheduling.models import ScheduleRequest, ScheduleRequestComment
from accounts.models import User
from django.utils import timezone

def sidebar_context(request):
    """
    Context processor to provide counts for the sidebar and header notifications
    """
    context = {
        'pending_requests_count': 0,
        'pending_count': 0,
        'notifications_count': 0,
        'notifications': [],
    }
    
    if not request.user.is_authenticated:
        return context
    
    # Notifications for both user types
    notifications = []
    
    if request.user.user_type == 'technician':
        # Count pending appointment requests
        pending_requests = ScheduleRequest.objects.filter(status='pending').count()
        context['pending_requests_count'] = pending_requests
        
        # Count pending user approvals
        pending_users = User.objects.filter(is_approved=False).count()
        context['pending_count'] = pending_users
        
        # Unread messages from professors
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__status='pending',
            is_read=False
        ).exclude(author=request.user).select_related('author', 'schedule_request')
        
        # Create notifications for unread messages
        for message in unread_messages:
            notifications.append({
                'title': f'Mensagem de {message.author.get_full_name()}',
                'message': message.message[:50] + '...' if len(message.message) > 50 else message.message,
                'timestamp': message.created_at,
                'type': 'message',
                'url': f'/scheduling/request/{message.schedule_request.id}/',
                'icon': 'bi bi-chat-dots'
            })
        
        # Add notification for pending requests
        if pending_requests > 0:
            notifications.append({
                'title': 'Solicitações Pendentes',
                'message': f'{pending_requests} solicitação(ões) aguardando aprovação',
                'timestamp': None,
                'type': 'pending_requests',
                'url': '/scheduling/pending/',
                'icon': 'bi bi-hourglass-split'
            })
            
        # Add notification for pending user approvals
        if pending_users > 0:
            notifications.append({
                'title': 'Usuários Aguardando Aprovação',
                'message': f'{pending_users} usuário(s) aguardando aprovação',
                'timestamp': None,
                'type': 'pending_users',
                'url': '/accounts/pending-users/',
                'icon': 'bi bi-person-plus'
            })
    
    elif request.user.user_type == 'professor':
        # Unread messages from technicians
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__professor=request.user,
            is_read=False
        ).exclude(author=request.user).select_related('author', 'schedule_request')
        
        # Create notifications for unread messages
        for message in unread_messages:
            notifications.append({
                'title': f'Mensagem do Técnico',
                'message': message.message[:50] + '...' if len(message.message) > 50 else message.message,
                'timestamp': message.created_at,
                'type': 'message',
                'url': f'/scheduling/request/{message.schedule_request.id}/',
                'icon': 'bi bi-chat-dots'
            })
        
        # Check for approved/rejected requests
        recent_reviews = ScheduleRequest.objects.filter(
            professor=request.user,
            status__in=['approved', 'rejected'],
            review_date__isnull=False
        ).order_by('-review_date')[:3]
        
        for review in recent_reviews:
            status_text = 'aprovada' if review.status == 'approved' else 'rejeitada'
            notifications.append({
                'title': f'Solicitação {status_text}',
                'message': f'Sua solicitação para {review.laboratory.name} foi {status_text}',
                'timestamp': review.review_date,
                'type': 'status_update',
                'url': f'/scheduling/request/{review.id}/',
                'icon': 'bi bi-check-circle' if review.status == 'approved' else 'bi bi-x-circle'
            })
    
    # Sort notifications by timestamp (most recent first)
    notifications.sort(key=lambda x: x['timestamp'] or timezone.now(), reverse=True)
    
    context['notifications'] = notifications[:10]  # Limit to 10 most recent
    
    # Count total notifications for the badge (unread messages + pending items)
    if request.user.user_type == 'technician':
        # Count unread messages from professors
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__status='pending',
            is_read=False
        ).exclude(author=request.user).count()
        
        # Add pending requests and pending users to the count
        total_count = unread_messages + pending_requests + pending_users
        
    elif request.user.user_type == 'professor':
        # Count unread messages from technicians
        unread_messages = ScheduleRequestComment.objects.filter(
            schedule_request__professor=request.user,
            is_read=False
        ).exclude(author=request.user).count()
        
        # Count recent status updates (approved/rejected) not yet acknowledged
        recent_status_updates = ScheduleRequest.objects.filter(
            professor=request.user,
            status__in=['approved', 'rejected'],
            review_date__isnull=False,
            review_date__gte=timezone.now() - timezone.timedelta(days=7)  # Last 7 days
        ).count()
        
        total_count = unread_messages + recent_status_updates
        
    else:
        total_count = 0
    
    context['notifications_count'] = total_count
    
    return context