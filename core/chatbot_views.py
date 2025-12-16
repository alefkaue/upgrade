"""
Financial Sniper - Views do Chatbot
Endpoints para o agente de IA com análise financeira
"""

import json
import os
import re
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from groq import Groq
from serpapi import GoogleSearch

from .models import Project, Item
from .financial_services import FinancialSniper


GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
SERPAPI_KEY = os.environ.get('SERPAPI_KEY', '')

financial_sniper = FinancialSniper()


def get_groq_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def search_product_prices(query: str, num_results: int = 5) -> list:
    """
    Busca preços de produtos usando SerpApi
    """
    if not SERPAPI_KEY:
        return []
    
    try:
        search = GoogleSearch({
            "q": f"{query} preço comprar",
            "location": "Brazil",
            "hl": "pt",
            "gl": "br",
            "api_key": SERPAPI_KEY,
            "num": num_results,
        })
        
        results = search.get_dict()
        
        products = []
        
        if 'shopping_results' in results:
            for item in results['shopping_results'][:num_results]:
                price_str = item.get('price', '')
                price = financial_sniper.parse_price(price_str)
                
                products.append({
                    'name': item.get('title', ''),
                    'price': price,
                    'price_formatted': price_str,
                    'store': item.get('source', 'Desconhecido'),
                    'link': item.get('link', ''),
                    'image': item.get('thumbnail', ''),
                })
        
        if 'organic_results' in results and len(products) < num_results:
            for item in results['organic_results'][:num_results - len(products)]:
                snippet = item.get('snippet', '')
                price_match = re.search(r'R\$\s*[\d.,]+', snippet)
                price = None
                price_str = ''
                
                if price_match:
                    price_str = price_match.group()
                    price = financial_sniper.parse_price(price_str)
                
                if price:
                    products.append({
                        'name': item.get('title', ''),
                        'price': price,
                        'price_formatted': price_str,
                        'store': item.get('displayed_link', 'Web'),
                        'link': item.get('link', ''),
                        'image': '',
                    })
        
        return products
        
    except Exception as e:
        return []


def build_system_prompt(user_context: dict) -> str:
    """
    Constrói o prompt do sistema com contexto financeiro completo do usuário
    """
    dollar_info = financial_sniper.get_dollar_quote()
    
    financial_profile = ""
    if user_context.get('user'):
        u = user_context['user']
        financial_profile = f"""
PERFIL FINANCEIRO DO USUÁRIO:
- Renda Mensal: R$ {u.get('monthly_income', 0):.2f}
- Gastos Fixos: R$ {u.get('fixed_expenses', 0):.2f}
- Fluxo Livre: R$ {u.get('free_cash_flow', 0):.2f}
- Disponível para Compras: R$ {u.get('available_cash', 0):.2f}
- Total Comprometido: R$ {u.get('total_committed', 0):.2f}
- % Comprometimento: {u.get('commitment_percentage', 0):.1f}%
- Status: {'⚠️ SOBRE-COMPROMETIDO' if u.get('is_over_committed') else '✅ Saudável'}
"""
    
    projects_info = ""
    if user_context.get('projects'):
        projects_info = "\nPROJETOS ATIVOS:\n"
        for p in user_context['projects']:
            projects_info += f"- [{p['id']}] {p['name']}: Total R$ {p['total']:.2f} | Parcela/mês: R$ {p.get('monthly_installment', 0):.2f}\n"
            if p.get('items'):
                for item in p['items'][:5]:
                    projects_info += f"    └ {item['name']}: R$ {item['price']:.2f} ({item['store']})\n"
    
    return f"""Você é o Financial Sniper, um estrategista financeiro inteligente para compras.

CONTEXTO ATUAL:
- Cotação do Dólar: {dollar_info['formatted']}
- Inflação anual: 4.5%
{financial_profile}
{projects_info}

SUA MISSÃO PRINCIPAL:
Você NÃO é passivo. Você ANALISA ativamente o perfil financeiro do usuário e dá recomendações PERSONALIZADAS.
Quando o usuário menciona um produto, você DEVE cruzar o preço com a renda dele e recomendar:
1. Se ele pode pagar à vista ou precisa parcelar
2. Qual loja oferece o melhor cenário para O PERFIL DELE (não o mais barato geral)
3. Quantas parcelas cabem no orçamento dele

EXEMPLO DE ANÁLISE (use este formato):
"Para sua renda de R$ 3.000, esse item de R$ 5.000 vai pesar. 
A Loja X parcela em 21x sem juros = R$ 238/mês (8% da renda - CABE).
A Loja Y é R$ 200 mais barata mas só divide em 10x = R$ 480/mês (16% da renda - PESADO).
Recomendo a Loja X."

COMANDOS DE AUTOMAÇÃO (use para modificar o banco de dados):
- [SALVAR_ITEM:projeto_id,nome,preco_vista,preco_parcelado,parcelas,loja,link] - Adicionar item
- [ATUALIZAR_ITEM:item_id,campo,novo_valor] - Atualizar item existente
- [TROCAR_ITEM:item_id,novo_nome,novo_preco,nova_loja,novo_link] - Substituir item por alternativa
- [ANALISAR_ACESSIBILIDADE:preco_vista,preco_parcelado,parcelas] - Verificar se cabe no orçamento

COMANDOS DE CÁLCULO:
- [CALCULAR_IMPORT:preço_usd,frete_usd,preço_nacional_brl] - Importação
- [ANALISAR_PAGAMENTO:à_vista,parcelado,parcelas,sem_juros] - Forma de pagamento

REGRAS:
1. SEMPRE cruze preços com a renda do usuário
2. Se ele pedir para trocar um item, busque alternativas e EXECUTE a troca automaticamente
3. Seja proativo: se detectar um item muito caro para o perfil, ALERTE
4. Use valores específicos, nunca generalize

Responda em português brasileiro, de forma amigável mas direta."""


def parse_ai_commands(response_text: str, user) -> tuple:
    """
    Processa comandos especiais na resposta da IA
    Retorna (resposta_processada, resultados_extras)
    """
    extras = []
    processed = response_text
    
    import_pattern = r'\[CALCULAR_IMPORT:([^,]+),([^,]+),([^\]]+)\]'
    for match in re.finditer(import_pattern, response_text):
        try:
            price_usd = float(match.group(1).strip())
            shipping_usd = float(match.group(2).strip())
            national_brl = float(match.group(3).strip()) if match.group(3).strip() != 'null' else None
            
            if national_brl is not None:
                result = financial_sniper.analyze_import(
                    price_usd, 
                    shipping_usd, 
                    float(national_brl)
                )
            else:
                result = financial_sniper.analyze_import(
                    price_usd, 
                    shipping_usd
                )
            
            extras.append({
                'type': 'import_analysis',
                'data': result
            })
            
            replacement = f"\n\n📦 **Análise de Importação:**\n"
            replacement += f"- Preço em USD: US$ {price_usd:.2f}\n"
            replacement += f"- Cotação do dólar: R$ {result.get('import_analysis', result).get('dollar_rate', result.get('dollar_rate', 0)):.4f}\n"
            
            if 'import_analysis' in result:
                imp = result['import_analysis']
                replacement += f"- Valor base: R$ {imp['base_brl']:.2f}\n"
                replacement += f"- Imposto importação ({imp['import_tax_rate']*100:.0f}%): R$ {imp['import_tax_brl']:.2f}\n"
                replacement += f"- ICMS ({imp['icms_rate']*100:.0f}%): R$ {imp['icms_brl']:.2f}\n"
                replacement += f"- **Total importado: R$ {imp['total_brl']:.2f}**\n"
                replacement += f"\n{result['recommendation_text']}\n"
            else:
                replacement += f"- Valor base: R$ {result['base_brl']:.2f}\n"
                replacement += f"- Imposto importação: R$ {result['import_tax_brl']:.2f}\n"
                replacement += f"- ICMS: R$ {result['icms_brl']:.2f}\n"
                replacement += f"- **Total: R$ {result['total_brl']:.2f}**\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    payment_pattern = r'\[ANALISAR_PAGAMENTO:([^,]+),([^,]+),([^,]+),([^\]]+)\]'
    for match in re.finditer(payment_pattern, response_text):
        try:
            cash_price = float(match.group(1).strip())
            installment_price = float(match.group(2).strip())
            num_installments = int(match.group(3).strip())
            interest_free = match.group(4).strip().lower() in ['true', 'sim', '1', 'yes']
            
            result = financial_sniper.analyze_payment(
                cash_price,
                installment_price,
                num_installments,
                interest_free
            )
            
            extras.append({
                'type': 'payment_analysis',
                'data': result
            })
            
            replacement = f"\n\n💳 **Análise de Pagamento:**\n"
            replacement += f"- À vista: R$ {result['cash_price']:.2f}\n"
            replacement += f"- Parcelado: R$ {result['installment_price']:.2f} ({num_installments}x de R$ {result['monthly_installment']:.2f})\n"
            replacement += f"- Desconto à vista: {result['cash_discount_percentage']:.1f}%\n"
            
            if interest_free:
                replacement += f"- Economia com inflação (parcelando): R$ {result['inflation_savings']:.2f}\n"
            
            replacement += f"\n✅ **Recomendação:** {result['recommendation_text']}\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    save_pattern = r'\[SALVAR_ITEM:([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,\]]+)(?:,([^\]]+))?\]'
    for match in re.finditer(save_pattern, response_text):
        try:
            project_id = int(match.group(1).strip())
            name = match.group(2).strip()
            price_cash = float(match.group(3).strip())
            price_inst = float(match.group(4).strip())
            installments = int(match.group(5).strip())
            store = match.group(6).strip()
            link = match.group(7).strip() if match.group(7) else ''
            
            project = Project.objects.filter(pk=project_id, user=user).first()
            if project:
                valid_stores = ['kabum', 'amazon', 'pichau', 'terabyte', 'aliexpress', 'mercadolivre', 'magazineluiza']
                item = Item.objects.create(
                    project=project,
                    name=name,
                    cash_price=Decimal(str(price_cash)),
                    installment_price=Decimal(str(price_inst)),
                    installment_count=installments,
                    store=store.lower() if store.lower() in valid_stores else 'outro',
                    link=link if link else None,
                )
                
                extras.append({'type': 'item_saved', 'data': {'item_id': item.id, 'name': name, 'project': project.name}})
                replacement = f"\n\n✅ **Item adicionado!** {name}: R$ {price_cash:.2f} ({installments}x de R$ {price_inst/installments:.2f}) - {project.name}\n"
            else:
                replacement = f"\n\n❌ Projeto não encontrado.\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    trocar_pattern = r'\[TROCAR_ITEM:(\d+),([^,]+),([^,]+),([^,]+),([^\]]*)\]'
    for match in re.finditer(trocar_pattern, response_text):
        try:
            item_id = int(match.group(1).strip())
            new_name = match.group(2).strip()
            new_price = float(match.group(3).strip())
            new_store = match.group(4).strip()
            new_link = match.group(5).strip()
            
            item = Item.objects.filter(pk=item_id, project__user=user).first()
            if item:
                old_name = item.name
                old_price = item.cash_price
                item.name = new_name
                item.cash_price = Decimal(str(new_price))
                item.installment_price = Decimal(str(new_price))
                item.store = new_store.lower() if new_store.lower() in ['kabum', 'amazon', 'pichau', 'terabyte', 'aliexpress', 'mercadolivre', 'magazineluiza'] else 'outro'
                item.link = new_link if new_link else None
                item.save()
                
                savings = float(old_price) - new_price
                extras.append({'type': 'item_replaced', 'data': {'item_id': item.id, 'old_name': old_name, 'new_name': new_name, 'savings': savings}})
                replacement = f"\n\n🔄 **Item substituído!**\n❌ Removido: {old_name} (R$ {float(old_price):.2f})\n✅ Adicionado: {new_name} (R$ {new_price:.2f})\n💰 Economia: R$ {savings:.2f}\n"
            else:
                replacement = f"\n\n❌ Item não encontrado.\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    atualizar_pattern = r'\[ATUALIZAR_ITEM:(\d+),([^,]+),([^\]]+)\]'
    for match in re.finditer(atualizar_pattern, response_text):
        try:
            item_id = int(match.group(1).strip())
            field = match.group(2).strip().lower()
            new_value = match.group(3).strip()
            
            item = Item.objects.filter(pk=item_id, project__user=user).first()
            if item:
                allowed_fields = {'name': str, 'cash_price': Decimal, 'installment_price': Decimal, 'installment_count': int, 'store': str, 'link': str}
                if field in allowed_fields:
                    old_value = getattr(item, field)
                    if field in ['cash_price', 'installment_price']:
                        setattr(item, field, Decimal(new_value))
                    elif field == 'installment_count':
                        setattr(item, field, int(new_value))
                    else:
                        setattr(item, field, new_value)
                    item.save()
                    extras.append({'type': 'item_updated', 'data': {'item_id': item.id, 'field': field, 'old_value': str(old_value), 'new_value': new_value}})
                    replacement = f"\n\n✅ **Item atualizado!** {item.name}: {field} alterado para {new_value}\n"
                else:
                    replacement = f"\n\n❌ Campo não permitido: {field}\n"
            else:
                replacement = f"\n\n❌ Item não encontrado.\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    afford_pattern = r'\[ANALISAR_ACESSIBILIDADE:([^,]+),([^,]+),([^\]]+)\]'
    for match in re.finditer(afford_pattern, response_text):
        try:
            price_cash = float(match.group(1).strip())
            price_inst = float(match.group(2).strip())
            installments = int(match.group(3).strip())
            
            if user and hasattr(user, 'monthly_income'):
                result = financial_sniper.analyze_affordability(user, price_cash, price_inst, installments)
                risk_emoji = {'low': '✅', 'medium': '⚠️', 'high': '🔴', 'critical': '❌'}.get(result['risk_level'], '❓')
                replacement = f"\n\n{risk_emoji} **Análise de Acessibilidade:**\n- Estratégia: {result['strategy']}\n- Parcela: R$ {result['monthly_installment']:.2f}/mês ({result['installment_as_income_pct']:.1f}% da renda)\n- {result['reason']}\n"
                extras.append({'type': 'affordability_analysis', 'data': result})
            else:
                replacement = "\n\n❓ Faça login para análise personalizada.\n"
            
            processed = processed.replace(match.group(0), replacement)
        except Exception as e:
            pass
    
    search_pattern = r'\[BUSCAR_PRECO:([^\]]+)\]'
    processed = re.sub(search_pattern, '', processed)
    
    return processed, extras


@require_POST
def chatbot_message(request):
    """
    Endpoint principal do chatbot
    Recebe mensagem e retorna resposta com análise financeira
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        
        if not user_message:
            return JsonResponse({'error': 'Mensagem vazia'}, status=400)
        
        user_context = {'projects': [], 'user': None}
        if request.user.is_authenticated:
            u = request.user
            projects = Project.objects.filter(user=u)
            
            user_context['user'] = {
                'monthly_income': float(u.monthly_income),
                'fixed_expenses': float(u.fixed_expenses),
                'free_cash_flow': float(u.free_cash_flow),
                'available_cash': float(u.available_cash),
                'total_committed': float(u.total_committed),
                'commitment_percentage': float(u.commitment_percentage),
                'is_over_committed': u.is_over_committed,
            }
            
            user_context['projects'] = [
                {
                    'id': p.id,
                    'name': p.name,
                    'total': float(p.total_cash_price),
                    'budget': float(p.budget),
                    'monthly_installment': float(p.total_monthly_installment),
                    'items': [
                        {
                            'id': item.id,
                            'name': item.name,
                            'price': float(item.cash_price),
                            'store': item.store,
                        }
                        for item in p.items.all()[:5]
                    ]
                }
                for p in projects
            ]
        
        search_results = []
        product_keywords = ['preço', 'quanto custa', 'buscar', 'encontrar', 'procurar', 'comprar']
        should_search = any(kw in user_message.lower() for kw in product_keywords)
        
        if should_search and SERPAPI_KEY:
            search_query = re.sub(r'(quanto custa|preço|buscar|encontrar|procurar|comprar)', '', user_message, flags=re.IGNORECASE).strip()
            if search_query:
                search_results = search_product_prices(search_query)
        
        client = get_groq_client()
        
        if not client:
            response_text = process_without_ai(user_message, search_results, user_context)
            return JsonResponse({
                'response': response_text,
                'search_results': search_results,
                'extras': [],
            })
        
        messages = [
            {"role": "system", "content": build_system_prompt(user_context)}
        ]
        
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        search_context = ""
        if search_results:
            search_context = "\n\n[RESULTADOS DA BUSCA]:\n"
            for i, product in enumerate(search_results, 1):
                search_context += f"{i}. {product['name']} - {product['price_formatted']} ({product['store']})\n"
        
        messages.append({
            "role": "user",
            "content": user_message + search_context
        })
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            response_text = completion.choices[0].message.content
            
        except Exception as e:
            response_text = process_without_ai(user_message, search_results, user_context)
        
        user_for_parse = request.user if request.user.is_authenticated else None
        processed_response, extras = parse_ai_commands(response_text or "", user_for_parse)
        
        return JsonResponse({
            'response': processed_response,
            'search_results': search_results,
            'extras': extras,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def process_without_ai(message: str, search_results: list, user_context: dict) -> str:
    """
    Processa mensagem quando não há API key do Groq
    Fornece funcionalidade básica de cálculo
    """
    message_lower = message.lower()
    
    if 'dólar' in message_lower or 'cotação' in message_lower:
        quote = financial_sniper.get_dollar_quote()
        return f"💵 Cotação atual do Dólar: {quote['formatted']}\n\nAtualizado em: {quote['timestamp']}"
    
    import_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:dólares?|usd|\$)', message_lower)
    if import_match and ('import' in message_lower or 'taxa' in message_lower):
        price_usd = float(import_match.group(1).replace(',', '.'))
        result = financial_sniper.analyze_import(price_usd)
        
        return f"""📦 **Cálculo de Importação**

Preço: US$ {price_usd:.2f}
Cotação: R$ {result['dollar_rate']:.4f}

Breakdown:
- Valor base: R$ {result['base_brl']:.2f}
- Imposto ({result['import_tax_rate']*100:.0f}%): R$ {result['import_tax_brl']:.2f}
- ICMS (17%): R$ {result['icms_brl']:.2f}

**Total Final: R$ {result['total_brl']:.2f}**"""
    
    if search_results:
        response = "🔍 **Resultados encontrados:**\n\n"
        for i, product in enumerate(search_results, 1):
            response += f"{i}. **{product['name']}**\n"
            response += f"   💰 {product['price_formatted']} - {product['store']}\n\n"
        return response
    
    return """👋 Olá! Sou o **Financial Sniper**, seu assistente de compras inteligentes.

Posso ajudar você com:
• 💵 Cotação do dólar em tempo real
• 📦 Cálculo de impostos de importação
• 💳 Análise de parcelamento vs à vista
• 🔍 Busca de preços de produtos

Como posso ajudar?

*Nota: Configure a API Key do Groq para respostas mais inteligentes.*"""


@require_GET
def chatbot_dollar_quote(request):
    """
    Endpoint para obter cotação do dólar
    """
    quote = financial_sniper.get_dollar_quote()
    return JsonResponse(quote)


@require_POST
def chatbot_calculate_import(request):
    """
    Endpoint direto para cálculo de importação
    """
    try:
        data = json.loads(request.body)
        price_usd = float(data.get('price_usd', 0))
        shipping_usd = float(data.get('shipping_usd', 0))
        national_price = data.get('national_price_brl')
        is_remessa_conforme = data.get('is_remessa_conforme', True)
        
        if national_price:
            result = financial_sniper.analyze_import(
                price_usd, 
                shipping_usd, 
                float(national_price),
                is_remessa_conforme
            )
        else:
            result = financial_sniper.analyze_import(
                price_usd, 
                shipping_usd,
                is_remessa_conforme=is_remessa_conforme
            )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
def chatbot_analyze_payment(request):
    """
    Endpoint direto para análise de pagamento
    """
    try:
        data = json.loads(request.body)
        cash_price = float(data.get('cash_price', 0))
        installment_price = float(data.get('installment_price', 0))
        num_installments = int(data.get('num_installments', 1))
        interest_free = data.get('interest_free', True)
        
        result = financial_sniper.analyze_payment(
            cash_price,
            installment_price,
            num_installments,
            interest_free
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def chatbot_user_context(request):
    """
    Retorna contexto do usuário para o chatbot
    """
    user = request.user
    projects = Project.objects.filter(user=user)
    
    context = {
        'user': {
            'username': user.username,
            'monthly_income': float(user.monthly_income),
            'fixed_expenses': float(user.fixed_expenses),
            'free_cash_flow': float(user.free_cash_flow),
            'available_cash': float(user.available_cash),
        },
        'projects': [
            {
                'id': p.id,
                'name': p.name,
                'type': p.project_type,
                'budget': float(p.budget),
                'total_cash': float(p.total_cash_price),
                'total_installment': float(p.total_installment_price),
                'monthly_installment': float(p.total_monthly_installment),
                'items_count': p.items.count(),
            }
            for p in projects
        ],
        'financial': {
            'total_committed': float(user.total_committed),
            'commitment_percentage': float(user.commitment_percentage),
            'is_over_committed': user.is_over_committed,
        },
        'dollar_quote': financial_sniper.get_dollar_quote(),
    }
    
    return JsonResponse(context)
