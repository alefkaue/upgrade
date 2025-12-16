from decimal import Decimal


def financial_context(request):
    if not request.user.is_authenticated:
        return {}
    
    user = request.user
    
    financial_summary = {
        'monthly_income': float(user.monthly_income),
        'fixed_expenses': float(user.fixed_expenses),
        'safety_margin_value': float(user.safety_margin_value),
        'free_cash_flow': float(user.free_cash_flow),
        'total_committed': float(user.total_committed),
        'available_cash': float(user.available_cash),
        'commitment_percentage': float(user.commitment_percentage),
        'is_over_committed': user.is_over_committed,
    }
    
    notifications = []
    
    if user.monthly_income == 0:
        notifications.append({
            'type': 'info',
            'title': 'Configure seu perfil',
            'message': 'Adicione sua renda mensal para ver recomendacoes personalizadas.',
            'action_url': '?tab=profile',
            'action_text': 'Configurar',
        })
    
    if user.is_over_committed:
        notifications.append({
            'type': 'danger',
            'title': 'Alerta Financeiro',
            'message': f'Voce esta comprometendo {user.commitment_percentage:.0f}% do seu fluxo livre. Considere revisar suas parcelas.',
            'action_url': None,
            'action_text': None,
        })
    elif user.commitment_percentage > Decimal('50'):
        notifications.append({
            'type': 'warning',
            'title': 'Atencao',
            'message': f'Voce esta com {user.commitment_percentage:.0f}% do fluxo comprometido.',
            'action_url': None,
            'action_text': None,
        })
    
    if user.available_cash > 500 and user.commitment_percentage <= Decimal('30'):
        notifications.append({
            'type': 'success',
            'title': 'Saude Financeira',
            'message': f'Voce tem R$ {user.available_cash:.2f} disponiveis. Bom momento para investir!',
            'action_url': None,
            'action_text': None,
        })
    
    return {
        'financial_summary': financial_summary,
        'financial_notifications': notifications,
    }


def user_role_context(request):
    if not request.user.is_authenticated:
        return {}
    
    user = request.user
    
    return {
        'is_admin': user.is_admin_user,
        'is_partner': user.is_partner,
        'is_regular_user': user.is_regular_user,
        'user_role': user.role,
    }
