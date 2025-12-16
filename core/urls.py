from django.urls import path
from . import views
from . import chatbot_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/user/', views.dashboard_user, name='dashboard_user'),
    path('dashboard/partner/', views.dashboard_partner, name='dashboard_partner'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/projects/', views.admin_projects, name='admin_projects'),
    path('dashboard/admin/audit/', views.admin_audit, name='admin_audit'),
    path('dashboard/admin/master-links/', views.admin_master_links, name='admin_master_links'),
    path('dashboard/admin/master-links/update/', views.admin_update_master_links, name='admin_update_master_links'),
    path('dashboard/admin/users/<int:user_id>/projects/', views.admin_user_projects, name='admin_user_projects'),
    
    path('profile/update/', views.update_profile, name='update_profile'),
    path('partner/tags/', views.partner_update_tags, name='partner_update_tags'),
    
    path('project/new/', views.project_create, name='project_create'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('project/<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    path('project/<int:project_pk>/item/new/', views.item_create, name='item_create'),
    path('item/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('item/<int:pk>/delete/', views.item_delete, name='item_delete'),
    
    path('p/<slug:slug>/', views.partner_link, name='partner_link'),
    
    path('api/admin/edit/', views.admin_edit_inline, name='admin_edit_inline'),
    path('api/search/', views.api_product_search, name='api_product_search'),
    path('api/chat/', views.api_chat_action, name='api_chat_action'),
    path('api/for-you/', views.api_for_you, name='api_for_you'),
    path('api/smart-choice/', views.api_smart_choice, name='api_smart_choice'),
    
    path('api/chatbot/message/', chatbot_views.chatbot_message, name='chatbot_message'),
    path('api/chatbot/dollar/', chatbot_views.chatbot_dollar_quote, name='chatbot_dollar_quote'),
    path('api/chatbot/import/', chatbot_views.chatbot_calculate_import, name='chatbot_calculate_import'),
    path('api/chatbot/payment/', chatbot_views.chatbot_analyze_payment, name='chatbot_analyze_payment'),
    path('api/chatbot/context/', chatbot_views.chatbot_user_context, name='chatbot_user_context'),
]
