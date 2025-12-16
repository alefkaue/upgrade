from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PartnerProfile, AdminSettings, AuditLog, Project, Item, PartnerClick


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'corporate_id', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'corporate_id', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informacoes Corporativas', {
            'fields': ('corporate_id', 'role', 'slug', 'monthly_budget', 'monthly_income')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informacoes Corporativas', {
            'fields': ('corporate_id', 'role', 'monthly_budget')
        }),
    )


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'amazon_tag', 'kabum_id', 'total_clicks', 'total_earnings']
    search_fields = ['user__username', 'user__corporate_id']


@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    list_display = ['amazon_tag', 'kabum_id', 'terabyte_code']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['admin_id', 'user', 'action', 'model_name', 'object_repr', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['admin_id', 'user__username', 'object_repr']
    readonly_fields = ['user', 'admin_id', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent', 'timestamp']
    ordering = ['-timestamp']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'budget', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'user__username']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'store', 'cash_price', 'installment_price', 'created_at']
    list_filter = ['store', 'category']
    search_fields = ['name', 'project__name']


@admin.register(PartnerClick)
class PartnerClickAdmin(admin.ModelAdmin):
    list_display = ['partner', 'store', 'created_at', 'converted', 'earnings']
    list_filter = ['store', 'converted', 'created_at']
