# api/models.py
from django.db import models
from accounts.models import User

class AIFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    response = models.TextField()
    is_helpful = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback: {'Útil' if self.is_helpful else 'Não útil'} - {self.question[:30]}"