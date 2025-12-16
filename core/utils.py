from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(request, action, model_name=None, object_id=None, object_repr=None, changes=None):
    from .models import AuditLog
    
    user = request.user if request.user.is_authenticated else None
    admin_id = user.corporate_id if user and user.is_admin_user else None
    
    AuditLog.objects.create(
        user=user,
        admin_id=admin_id,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else None,
        object_repr=object_repr,
        changes=changes or {},
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )


def generate_affiliate_link(item, partner_user=None):
    from .models import AdminSettings
    
    if not item.link:
        return '#'
    
    store = item.store.lower() if item.store else ''
    base_url = item.link
    
    partner_tag = None
    if partner_user:
        try:
            partner_tag = partner_user.partner_profile.get_tag_for_store(store)
        except Exception:
            partner_tag = None
    
    if partner_tag:
        tag = partner_tag
    else:
        try:
            tag = AdminSettings.get_fallback_tag(store)
        except Exception:
            AdminSettings.objects.get_or_create(pk=1)
            tag = AdminSettings.get_fallback_tag(store)
    
    if not tag:
        return base_url
    
    parsed = urlparse(base_url)
    query_params = parse_qs(parsed.query)
    
    tag_param_names = {
        'amazon': 'tag',
        'kabum': 'pid',
        'terabyte': 'ref',
        'aliexpress': 'aff_id',
        'pichau': 'partner',
    }
    
    param_name = tag_param_names.get(store, 'ref')
    query_params[param_name] = [tag]
    
    new_query = urlencode(query_params, doseq=True)
    new_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return new_url


def check_budget_alert(user, monthly_payment):
    if user.monthly_budget > 0 and monthly_payment > user.monthly_budget:
        return {
            'alert': True,
            'message': f'Atenção: A parcela mensal (R$ {monthly_payment:.2f}) excede seu orçamento (R$ {user.monthly_budget:.2f})',
            'difference': monthly_payment - user.monthly_budget
        }
    return {'alert': False}
