# accounts/context_processors.py
from scheduling.models import ScheduleRequest
from accounts.models import User

def sidebar_context(request):
    """
    Context processor to provide counts for the sidebar notifications
    """
    context = {
        'pending_requests_count': 0,
        'pending_count': 0,
    }
    
    if request.user.is_authenticated and request.user.is_approved and request.user.user_type == 'technician':
        # Count pending appointment requests
        context['pending_requests_count'] = ScheduleRequest.objects.filter(status='pending').count()
        
        # Count pending user approvals
        context['pending_count'] = User.objects.filter(is_approved=False).count()
    
    return context