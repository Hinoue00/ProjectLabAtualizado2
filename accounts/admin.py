# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_approved', 'registration_date')
    list_filter = ('user_type', 'is_approved', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-registration_date',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Tipo de Usuário', {'fields': ('user_type', 'lab_department')}),
        ('Permissões', {'fields': ('is_approved', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}), 
    )
    
    # Adiciona ação de aprovação em massa
    actions = ['approve_users']
    
    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} usuários foram aprovados com sucesso.")
    approve_users.short_description = "Aprovar usuários selecionados"

admin.site.register(User, CustomUserAdmin)