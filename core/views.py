from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_POST
from decimal import Decimal
from functools import wraps


def admin_required(view_func):
    """Decorator to require admin user access"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Acesso negado.')
            return redirect('login')
        if not request.user.is_admin_user:
            messages.error(request, 'Acesso restrito a administradores.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

from .models import User, PartnerProfile, AuditLog, Project, Item, PartnerClick, AdminSettings
from .forms import UnifiedLoginForm, PartnerTagsForm, ProjectForm, ItemForm, UserRegistrationForm, UserProfileForm
from .utils import log_audit
from .finance_engine import FinanceEngine
import json


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=identifier, password=password)
        
        if user is not None:
            login(request, user)
            log_audit(request, 'login')
            messages.success(request, f'Bem-vindo, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Credenciais inválidas. Verifique usuário e senha.')
    
    form = UnifiedLoginForm()
    return render(request, 'core/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        monthly_budget = request.POST.get('monthly_budget', '0')
        
        if password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'core/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este usuário já existe.')
            return render(request, 'core/register.html')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                monthly_budget=Decimal(monthly_budget) if monthly_budget else Decimal('0'),
            )
            login(request, user)
            messages.success(request, 'Conta criada com sucesso!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Erro ao criar conta: {str(e)}')
    
    return render(request, 'core/register.html')


@login_required
def logout_view(request):
    log_audit(request, 'logout')
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('landing')


@login_required
def dashboard(request):
    user = request.user
    tab = request.GET.get('tab', 'overview')
    edit_mode = request.GET.get('edit', 'false') == 'true'
    
    projects = Project.objects.filter(user=user)
    total_projects = projects.count()
    
    if user.monthly_income > 0:
        fixed_pct = (user.fixed_expenses / user.monthly_income) * 100
        safety_pct = user.safety_margin
        committed_pct = (user.total_committed / user.monthly_income) * 100
        free_pct = 100 - float(fixed_pct) - float(safety_pct) - float(committed_pct)
    else:
        fixed_pct = safety_pct = committed_pct = free_pct = 0
    
    thermometer = {
        'fixed_pct': float(fixed_pct),
        'safety_pct': float(safety_pct),
        'committed_pct': float(committed_pct),
        'free_pct': max(0, float(free_pct)),
    }
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'thermometer': thermometer,
        'active_tab': tab,
        'edit_mode': edit_mode,
    }
    
    if user.is_admin_user:
        stats = {
            'total_users': User.objects.count(),
            'total_partners': User.objects.filter(role='partner').count(),
            'total_projects': Project.objects.count(),
            'total_items': Item.objects.count(),
        }
        recent_logs = AuditLog.objects.all()[:10]
        context['stats'] = stats
        context['recent_logs'] = recent_logs
    
    if user.is_partner or user.is_admin_user:
        partner_profile, _ = PartnerProfile.objects.get_or_create(user=user)
        total_clicks = PartnerClick.objects.filter(partner=user).count()
        total_earnings = PartnerClick.objects.filter(partner=user).aggregate(Sum('earnings'))['earnings__sum'] or Decimal('0')
        total_conversions = PartnerClick.objects.filter(partner=user, converted=True).count()
        recent_clicks = PartnerClick.objects.filter(partner=user)[:10]
        partner_link = request.build_absolute_uri(f'/p/{user.slug}/') if user.slug else ''
        
        context['partner_profile'] = partner_profile
        context['total_clicks'] = total_clicks
        context['total_earnings'] = total_earnings
        context['total_conversions'] = total_conversions
        context['recent_clicks'] = recent_clicks
        context['partner_link'] = partner_link
    
    return render(request, 'core/dashboard_unified.html', context)


@login_required
def dashboard_user(request):
    user = request.user
    projects = Project.objects.filter(user=user)
    total_projects = projects.count()
    
    total_monthly = sum(p.total_monthly_installment for p in projects)
    budget_exceeded = user.monthly_budget > 0 and total_monthly > user.monthly_budget
    
    financial_data = {
        'monthly_income': float(user.monthly_income),
        'fixed_expenses': float(user.fixed_expenses),
        'safety_margin_value': float(user.safety_margin_value),
        'free_cash_flow': float(user.free_cash_flow),
        'total_committed': float(user.total_committed),
        'available_cash': float(user.available_cash),
        'commitment_percentage': float(user.commitment_percentage),
        'is_over_committed': user.is_over_committed,
    }
    
    if user.monthly_income > 0:
        fixed_pct = (user.fixed_expenses / user.monthly_income) * 100
        safety_pct = user.safety_margin
        committed_pct = (user.total_committed / user.monthly_income) * 100
        free_pct = 100 - float(fixed_pct) - float(safety_pct) - float(committed_pct)
    else:
        fixed_pct = safety_pct = committed_pct = free_pct = 0
    
    thermometer = {
        'fixed_pct': float(fixed_pct),
        'safety_pct': float(safety_pct),
        'committed_pct': float(committed_pct),
        'free_pct': max(0, float(free_pct)),
    }
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'total_monthly': total_monthly,
        'budget_exceeded': budget_exceeded,
        'financial': financial_data,
        'thermometer': thermometer,
        'profile_form': UserProfileForm(instance=user),
    }
    return render(request, 'core/dashboard_user.html', context)


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            log_audit(request, 'update', 'User', request.user.id, 'Perfil Financeiro')
            messages.success(request, 'Perfil financeiro atualizado!')
    return redirect('dashboard_user')


@login_required
def dashboard_partner(request):
    user = request.user
    profile, created = PartnerProfile.objects.get_or_create(user=user)
    
    projects = Project.objects.filter(user=user)
    
    total_clicks = PartnerClick.objects.filter(partner=user).count()
    total_earnings = PartnerClick.objects.filter(partner=user).aggregate(Sum('earnings'))['earnings__sum'] or Decimal('0')
    total_conversions = PartnerClick.objects.filter(partner=user, converted=True).count()
    recent_clicks = PartnerClick.objects.filter(partner=user)[:10]
    
    partner_link = request.build_absolute_uri(f'/p/{user.slug}/') if user.slug else ''
    
    context = {
        'profile': profile,
        'projects': projects,
        'total_projects': projects.count(),
        'total_clicks': total_clicks,
        'total_earnings': total_earnings,
        'total_conversions': total_conversions,
        'recent_clicks': recent_clicks,
        'partner_link': partner_link,
        'tags_form': PartnerTagsForm(instance=profile),
    }
    return render(request, 'core/dashboard_partner.html', context)


@login_required
def dashboard_admin(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    edit_mode = request.GET.get('edit', 'false') == 'true'
    
    users = User.objects.all().order_by('-created_at')[:50]
    recent_logs = AuditLog.objects.all()[:50]
    
    stats = {
        'total_users': User.objects.count(),
        'total_partners': User.objects.filter(role='partner').count(),
        'total_projects': Project.objects.count(),
        'total_items': Item.objects.count(),
    }
    
    users_by_role = {
        'admins': User.objects.filter(role='admin').count(),
        'partners': User.objects.filter(role='partner').count(),
        'users': User.objects.filter(role='user').count(),
    }
    
    context = {
        'recent_logs': recent_logs,
        'stats': stats,
        'users_by_role': users_by_role,
        'recent_users': users[:5],
        'edit_mode': edit_mode,
        'active_tab': 'overview',
    }
    return render(request, 'core/dashboard_admin.html', context)


@login_required
def admin_users(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    edit_mode = request.GET.get('edit', 'false') == 'true'
    users = User.objects.all().order_by('-created_at')
    
    context = {
        'users': users,
        'edit_mode': edit_mode,
        'active_tab': 'users',
    }
    return render(request, 'core/admin_users.html', context)


@login_required
def admin_projects(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    edit_mode = request.GET.get('edit', 'false') == 'true'
    projects = Project.objects.all().order_by('-created_at')
    
    context = {
        'projects': projects,
        'edit_mode': edit_mode,
        'active_tab': 'projects',
    }
    return render(request, 'core/admin_projects.html', context)


@login_required
def admin_audit(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    edit_mode = request.GET.get('edit', 'false') == 'true'
    logs = AuditLog.objects.all().order_by('-timestamp')[:100]
    
    context = {
        'logs': logs,
        'edit_mode': edit_mode,
        'active_tab': 'audit',
    }
    return render(request, 'core/admin_audit.html', context)


@login_required
def partner_update_tags(request):
    if not request.user.is_partner:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    profile, _ = PartnerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = PartnerTagsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, 'update', 'PartnerProfile', profile.id, str(profile))
            messages.success(request, 'Tags atualizadas com sucesso!')
    
    return redirect('dashboard_partner')


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            
            log_audit(request, 'create', 'Project', project.id, project.name)
            messages.success(request, 'Projeto criado com sucesso!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Criar'})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Você não tem permissão para ver este projeto.')
        return redirect('dashboard')
    
    return render(request, 'core/project_detail.html', {'project': project})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    if project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_audit(request, 'update', 'Project', project.id, project.name)
            messages.success(request, 'Projeto atualizado!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Editar', 'project': project})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Você não tem permissão para excluir este projeto.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Projeto excluído com sucesso!')
        return redirect('dashboard')
    
    return render(request, 'core/project_confirm_delete.html', {'project': project})


@login_required
def item_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Você não tem permissão para adicionar itens a este projeto.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.project = project
            item.save()
            log_audit(request, 'create', 'Item', item.id, item.name)
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ItemForm()
    
    return render(request, 'core/item_form.html', {'form': form, 'project': project, 'action': 'Adicionar'})


@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Você não tem permissão para editar este item.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            log_audit(request, 'update', 'Item', item.id, item.name)
            messages.success(request, 'Item atualizado com sucesso!')
            return redirect('project_detail', pk=item.project.pk)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'core/item_form.html', {'form': form, 'item': item, 'project': item.project, 'action': 'Editar'})


@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.project.user != request.user and not request.user.is_admin_user:
        messages.error(request, 'Você não tem permissão para excluir este item.')
        return redirect('dashboard')
    
    project_pk = item.project.pk
    if request.method == 'POST':
        item.delete()
        log_audit(request, 'delete', 'Item', pk, item.name)
        messages.success(request, 'Item excluído com sucesso!')
        return redirect('project_detail', pk=project_pk)
    
    return render(request, 'core/item_confirm_delete.html', {'item': item})


def partner_link(request, slug):
    partner = get_object_or_404(User, slug=slug, role='partner')
    
    PartnerClick.objects.create(
        partner=partner,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referrer=request.META.get('HTTP_REFERER', ''),
    )
    
    profile, _ = PartnerProfile.objects.get_or_create(user=partner)
    profile.total_clicks += 1
    profile.save()
    
    return redirect('register')


@login_required
@require_POST
def admin_edit_inline(request):
    if not request.user.is_admin_user:
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    model_type = request.POST.get('model')
    object_id = request.POST.get('id')
    field = request.POST.get('field')
    value = request.POST.get('value')
    
    allowed_fields = {
        'project': ['name', 'description', 'budget'],
        'item': ['name', 'cash_price', 'installment_price', 'store'],
    }
    
    if model_type not in allowed_fields or field not in allowed_fields.get(model_type, []):
        return JsonResponse({'error': 'Campo não permitido'}, status=400)
    
    try:
        if model_type == 'project':
            obj = get_object_or_404(Project, pk=object_id)
            old_value = str(getattr(obj, field, ''))
            setattr(obj, field, value)
            obj.save()
            
            log_audit(request, 'update', 'Project', object_id, obj.name, 
                      changes={field: {'old': old_value, 'new': value}})
        
        elif model_type == 'item':
            obj = get_object_or_404(Item, pk=object_id)
            old_value = str(getattr(obj, field, ''))
            setattr(obj, field, value)
            obj.save()
            
            log_audit(request, 'update', 'Item', object_id, obj.name,
                      changes={field: {'old': old_value, 'new': value}})
        
        return JsonResponse({'success': True, 'new_value': value})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_product_search(request):
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        context = data.get('context', '')
        budget_cap = data.get('user_budget_cap', 0)
        preferred_payment = data.get('preferred_payment', 'installments')
        
        response = {
            'status': 'webhook_required',
            'message': 'Configure o webhook do n8n para busca de produtos',
            'payload_received': {
                'query': query,
                'context': context,
                'user_budget_cap': budget_cap,
                'preferred_payment': preferred_payment,
            },
            'expected_response_format': {
                'best_recommendation_id': 'store_id',
                'reasoning': 'Explicacao da IA',
                'items': [
                    {
                        'id': 'store_a',
                        'store': 'Amazon',
                        'price_cash': 1200.00,
                        'price_installments': 1200.00,
                        'installments_count': 10,
                        'monthly_value': 120.00,
                        'interest_free': True,
                        'url': 'https://...'
                    }
                ]
            }
        }
        return JsonResponse(response)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def api_chat_action(request):
    try:
        data = json.loads(request.body)
        action = data.get('action', '')
        project_id = data.get('project_id')
        message = data.get('message', '')
        
        if action == 'replace_expensive':
            project = get_object_or_404(Project, pk=project_id, user=request.user)
            items = project.items.order_by('-cash_price')
            
            if items.exists():
                most_expensive = items.first()
                original_price = most_expensive.cash_price
                new_price = original_price * Decimal('0.75')
                
                old_name = most_expensive.name
                most_expensive.cash_price = new_price
                most_expensive.installment_price = new_price
                most_expensive.name = f"{old_name} (Alternativa)"
                most_expensive.save()
                
                savings = original_price - new_price
                
                return JsonResponse({
                    'success': True,
                    'action': 'replace_expensive',
                    'message': f'Substituido: {old_name} por alternativa mais barata (Economia: R$ {savings:.2f})',
                    'old_item': old_name,
                    'new_price': float(new_price),
                    'savings': float(savings),
                })
            
            return JsonResponse({'error': 'Nenhum item encontrado'}, status=404)
        
        return JsonResponse({
            'status': 'ok',
            'message': 'Acao recebida',
            'action': action,
            'project_id': project_id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@admin_required
def admin_master_links(request):
    
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    
    context = {
        'admin_settings': admin_settings,
        'active_tab': 'master_links',
        'edit_mode': request.GET.get('edit', 'false') == 'true',
    }
    return render(request, 'core/admin_master_links.html', context)


@admin_required
@require_POST
def admin_update_master_links(request):
    
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    
    admin_settings.amazon_tag = request.POST.get('amazon_tag', admin_settings.amazon_tag)
    admin_settings.kabum_id = request.POST.get('kabum_id', admin_settings.kabum_id)
    admin_settings.terabyte_code = request.POST.get('terabyte_code', admin_settings.terabyte_code)
    admin_settings.aliexpress_id = request.POST.get('aliexpress_id', admin_settings.aliexpress_id)
    admin_settings.pichau_id = request.POST.get('pichau_id', admin_settings.pichau_id)
    admin_settings.save()
    
    log_audit(request, 'update', 'AdminSettings', 1, 'Links Mestres')
    messages.success(request, 'Links mestres atualizados com sucesso!')
    return redirect('admin_master_links')


@admin_required
def admin_user_projects(request, user_id):
    
    target_user = get_object_or_404(User, pk=user_id)
    projects = Project.objects.filter(user=target_user).order_by('-created_at')
    
    context = {
        'target_user': target_user,
        'projects': projects,
        'active_tab': 'users',
        'edit_mode': request.GET.get('edit', 'false') == 'true',
    }
    return render(request, 'core/admin_user_projects.html', context)


@login_required
def api_for_you(request):
    user = request.user
    projects = Project.objects.filter(user=user)
    
    suggestions = []
    engine = FinanceEngine()
    
    for project in projects[:3]:
        suggestion = engine.get_project_suggestions(project)
        if suggestion.get('missing_items'):
            suggestions.append({
                'project_id': project.pk,
                'project_name': project.name,
                'project_type': project.get_project_type_display(),
                'missing_count': len(suggestion.get('missing_items', [])),
                'ai_suggestions': suggestion.get('ai_suggestions', {}),
            })
    
    return render(request, 'core/partials/for_you.html', {'suggestions': suggestions})


@login_required
def api_smart_choice(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo nao permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        store_options = data.get('store_options', [])
        
        if not store_options:
            return JsonResponse({'error': 'Nenhuma opcao de loja fornecida'}, status=400)
        
        engine = FinanceEngine()
        result = engine.analyze_purchase_for_user(request.user, store_options)
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
