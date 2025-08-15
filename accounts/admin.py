# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PasswordResetRequest

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


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'status', 'requested_at', 'approved_by', 'whatsapp_sent')
    list_filter = ('status', 'whatsapp_sent', 'requested_at', 'approved_at')
    search_fields = ('email', 'user__first_name', 'user__last_name')
    readonly_fields = ('token', 'requested_at', 'approved_at', 'whatsapp_sent_at')
    ordering = ('-requested_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'user', 'status')}),
        ('Aprovação', {'fields': ('approved_by', 'approved_at')}),
        ('WhatsApp', {'fields': ('whatsapp_sent', 'whatsapp_sent_at')}),
        ('Segurança', {'fields': ('token', 'expires_at')}),
        ('Datas', {'fields': ('requested_at',)}),
    )