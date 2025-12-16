"""
Finance Engine - Motor de Inteligencia Financeira
Implementa o algoritmo Smart Choice (Renda vs. Preco) e recomendacoes contextuais
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
import os
import json

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class SmartChoiceEngine:
    """
    Algoritmo Smart Choice - Recomendacao baseada em Fluxo de Caixa
    
    Logica de Decisao:
    1. Calcula a "Capacidade de Parcela" (30% da renda livre)
    2. Cenario 1: Se usuario tem valor total disponivel -> Recomenda menor preco a vista (Pix)
    3. Cenario 2: Se valor a vista compromete a renda, busca parcelamento longo (12x, 18x, 21x)
       desde que a parcela caiba na "Capacidade Mensal"
    """
    
    SAFE_COMMITMENT_PCT = Decimal('30')
    MODERATE_COMMITMENT_PCT = Decimal('50')
    HIGH_COMMITMENT_PCT = Decimal('70')
    
    @classmethod
    def calculate_payment_capacity(
        cls,
        monthly_income: Decimal,
        fixed_expenses: Decimal,
        safety_margin_pct: Decimal = Decimal('10'),
        current_commitments: Decimal = Decimal('0')
    ) -> Dict:
        """
        Calcula a capacidade de pagamento do usuario
        """
        safety_margin = (monthly_income * safety_margin_pct) / Decimal('100')
        free_cash_flow = monthly_income - fixed_expenses - safety_margin
        available_for_new = free_cash_flow - current_commitments
        
        safe_installment_capacity = (free_cash_flow * cls.SAFE_COMMITMENT_PCT) / Decimal('100')
        max_installment_capacity = (free_cash_flow * cls.MODERATE_COMMITMENT_PCT) / Decimal('100')
        
        return {
            'monthly_income': float(monthly_income),
            'fixed_expenses': float(fixed_expenses),
            'safety_margin': float(safety_margin),
            'free_cash_flow': float(free_cash_flow),
            'current_commitments': float(current_commitments),
            'available_for_new': float(available_for_new),
            'safe_installment_capacity': float(safe_installment_capacity),
            'max_installment_capacity': float(max_installment_capacity),
        }
    
    @classmethod
    def smart_choice(
        cls,
        user_available_cash: Decimal,
        user_monthly_capacity: Decimal,
        store_options: List[Dict]
    ) -> Dict:
        """
        Algoritmo Smart Choice - Escolhe a melhor opcao de compra baseado no perfil financeiro
        
        Args:
            user_available_cash: Valor disponivel para compra a vista
            user_monthly_capacity: Capacidade mensal para parcelas
            store_options: Lista de opcoes de lojas com precos
            
        Returns:
            Dict com a recomendacao e analise completa
        """
        if not store_options:
            return {'error': 'Nenhuma opcao de loja fornecida'}
        
        analyzed_options = []
        
        for opt in store_options:
            store = opt.get('store', 'Desconhecida')
            price_cash = Decimal(str(opt.get('price_cash', 0)))
            price_installment = Decimal(str(opt.get('price_installment', price_cash)))
            installment_count = opt.get('installment_count', 1)
            interest_free = opt.get('interest_free', True)
            url = opt.get('url', '')
            
            monthly_installment = price_installment / installment_count if installment_count > 0 else price_installment
            
            can_afford_cash = user_available_cash >= price_cash
            can_afford_installment = user_monthly_capacity >= monthly_installment
            
            cash_discount = price_installment - price_cash
            cash_discount_pct = (cash_discount / price_installment * 100) if price_installment > 0 else Decimal('0')
            
            commitment_pct = (monthly_installment / user_monthly_capacity * 100) if user_monthly_capacity > 0 else Decimal('999')
            
            score = cls._calculate_option_score(
                can_afford_cash=can_afford_cash,
                can_afford_installment=can_afford_installment,
                cash_discount_pct=cash_discount_pct,
                interest_free=interest_free,
                installment_count=installment_count,
                commitment_pct=commitment_pct,
                price_cash=price_cash
            )
            
            analyzed_options.append({
                'store': store,
                'price_cash': float(price_cash),
                'price_installment': float(price_installment),
                'installment_count': installment_count,
                'monthly_installment': float(monthly_installment.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                'interest_free': interest_free,
                'can_afford_cash': can_afford_cash,
                'can_afford_installment': can_afford_installment,
                'cash_discount': float(cash_discount.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                'cash_discount_pct': float(cash_discount_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
                'commitment_pct': float(commitment_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
                'score': score,
                'url': url,
            })
        
        analyzed_options.sort(key=lambda x: x['score'], reverse=True)
        
        best = analyzed_options[0]
        
        recommendation = cls._generate_recommendation(best, user_available_cash, user_monthly_capacity)
        
        return {
            'best_option': best,
            'all_options': analyzed_options,
            'recommendation': recommendation,
            'user_available_cash': float(user_available_cash),
            'user_monthly_capacity': float(user_monthly_capacity),
        }
    
    @classmethod
    def _calculate_option_score(
        cls,
        can_afford_cash: bool,
        can_afford_installment: bool,
        cash_discount_pct: Decimal,
        interest_free: bool,
        installment_count: int,
        commitment_pct: Decimal,
        price_cash: Decimal
    ) -> float:
        """Calcula score de uma opcao (0-100)"""
        score = 0.0
        
        if can_afford_cash and cash_discount_pct >= Decimal('10'):
            score = 95 + float(cash_discount_pct) * 0.1
        elif can_afford_installment and interest_free:
            if installment_count >= 18:
                score = 90 - float(commitment_pct) * 0.2
            elif installment_count >= 12:
                score = 85 - float(commitment_pct) * 0.2
            else:
                score = 75 - float(commitment_pct) * 0.3
        elif can_afford_cash:
            score = 70 + float(cash_discount_pct) * 0.5
        elif can_afford_installment:
            score = 50 - float(commitment_pct) * 0.3
        else:
            score = max(0, 20 - float(price_cash) / 1000)
        
        return round(max(0, min(100, score)), 1)
    
    @classmethod
    def _generate_recommendation(
        cls,
        best_option: Dict,
        user_available_cash: Decimal,
        user_monthly_capacity: Decimal
    ) -> Dict:
        """Gera recomendacao textual para o usuario"""
        store = best_option['store']
        
        if best_option['can_afford_cash'] and best_option['cash_discount_pct'] >= 10:
            strategy = 'cash'
            title = 'Pague a Vista!'
            message = (
                f"Recomendado: {store} a vista por R$ {best_option['price_cash']:.2f}. "
                f"Economia de R$ {best_option['cash_discount']:.2f} ({best_option['cash_discount_pct']:.1f}% de desconto)."
            )
            risk_level = 'low'
        elif best_option['can_afford_installment'] and best_option['interest_free']:
            strategy = 'installment'
            title = 'Parcele sem Juros'
            message = (
                f"Recomendado: {store} em {best_option['installment_count']}x de "
                f"R$ {best_option['monthly_installment']:.2f} sem juros. "
                f"Cabe no seu bolso!"
            )
            if best_option['commitment_pct'] <= 30:
                risk_level = 'low'
            elif best_option['commitment_pct'] <= 50:
                risk_level = 'medium'
            else:
                risk_level = 'high'
        elif best_option['can_afford_cash']:
            strategy = 'cash'
            title = 'Compra a Vista'
            message = (
                f"Voce pode comprar na {store} a vista por R$ {best_option['price_cash']:.2f}. "
                f"Sem comprometer seu fluxo mensal."
            )
            risk_level = 'low'
        elif best_option['can_afford_installment']:
            strategy = 'installment_caution'
            title = 'Parcelamento com Cautela'
            message = (
                f"{store} oferece {best_option['installment_count']}x de "
                f"R$ {best_option['monthly_installment']:.2f}, mas isso compromete "
                f"{best_option['commitment_pct']:.0f}% do seu fluxo. Avalie com cuidado."
            )
            risk_level = 'high'
        else:
            strategy = 'not_recommended'
            title = 'Fora do Orcamento'
            message = (
                f"Este produto esta acima do seu orcamento atual. "
                f"Considere economizar ou buscar alternativas mais baratas."
            )
            risk_level = 'critical'
        
        return {
            'strategy': strategy,
            'title': title,
            'message': message,
            'risk_level': risk_level,
            'store': store,
        }


class ForYouRecommendationEngine:
    """
    Motor de Recomendacoes "For You" usando IA (Groq)
    Sugere itens faltantes baseado no tipo de projeto
    """
    
    PROJECT_TYPE_SUGGESTIONS = {
        'pc': [
            'Placa de Video (GPU)',
            'Processador (CPU)',
            'Memoria RAM',
            'SSD/HD',
            'Placa Mae',
            'Fonte',
            'Gabinete',
            'Cooler',
            'Monitor',
            'Teclado',
            'Mouse',
            'Headset',
        ],
        'casa': [
            'Sofa',
            'Mesa de Jantar',
            'Cama',
            'Guarda-roupa',
            'TV',
            'Ar Condicionado',
            'Geladeira',
            'Fogao',
            'Micro-ondas',
        ],
        'eletro': [
            'Geladeira',
            'Fogao',
            'Maquina de Lavar',
            'Micro-ondas',
            'Ar Condicionado',
            'Aspirador de Po',
        ],
        'moveis': [
            'Sofa',
            'Cama',
            'Mesa',
            'Cadeiras',
            'Guarda-roupa',
            'Estante',
            'Rack',
        ],
        'eletronicos': [
            'Smartphone',
            'Tablet',
            'Notebook',
            'Smart TV',
            'Fone de Ouvido',
            'Smartwatch',
        ],
    }
    
    def __init__(self):
        self.groq_client = None
        if GROQ_AVAILABLE:
            api_key = os.environ.get('GROQ_API_KEY')
            if api_key:
                self.groq_client = Groq(api_key=api_key)
    
    def get_suggestions_for_project(
        self,
        project_name: str,
        project_type: str,
        existing_items: List[str]
    ) -> Dict:
        """
        Retorna sugestoes de itens faltantes para um projeto
        """
        base_suggestions = self.PROJECT_TYPE_SUGGESTIONS.get(project_type, [])
        
        existing_lower = [item.lower() for item in existing_items]
        missing_items = []
        
        for suggestion in base_suggestions:
            if not any(suggestion.lower() in existing or existing in suggestion.lower() for existing in existing_lower):
                missing_items.append(suggestion)
        
        if self.groq_client and missing_items:
            ai_suggestions = self._get_ai_suggestions(project_name, project_type, existing_items, missing_items)
        else:
            ai_suggestions = {
                'suggestions': missing_items[:5],
                'reasoning': 'Baseado no tipo de projeto selecionado.',
                'priority_order': missing_items[:3],
            }
        
        return {
            'project_name': project_name,
            'project_type': project_type,
            'existing_items': existing_items,
            'missing_items': missing_items,
            'ai_suggestions': ai_suggestions,
        }
    
    def _get_ai_suggestions(
        self,
        project_name: str,
        project_type: str,
        existing_items: List[str],
        missing_items: List[str]
    ) -> Dict:
        """Usa Groq para gerar sugestoes inteligentes"""
        try:
            prompt = f"""
            Analise este projeto de compra e sugira os itens mais importantes que estao faltando.
            
            Nome do Projeto: {project_name}
            Tipo: {project_type}
            Itens ja adicionados: {', '.join(existing_items) if existing_items else 'Nenhum'}
            Itens possivelmente faltando: {', '.join(missing_items)}
            
            Responda em JSON com este formato:
            {{
                "suggestions": ["item1", "item2", "item3"],
                "reasoning": "Explicacao breve do porque estes itens sao importantes",
                "priority_order": ["item_mais_importante", "segundo_mais_importante", "terceiro"]
            }}
            
            Considere compatibilidade e necessidade real baseado no nome do projeto.
            Responda apenas o JSON, sem texto adicional.
            """
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            return {
                'suggestions': missing_items[:5],
                'reasoning': f'Sugestoes baseadas no tipo de projeto.',
                'priority_order': missing_items[:3],
            }


class FinanceEngine:
    """
    Classe principal que integra Smart Choice e For You
    """
    
    def __init__(self):
        self.smart_choice = SmartChoiceEngine()
        self.for_you = ForYouRecommendationEngine()
    
    def analyze_purchase_for_user(
        self,
        user,
        store_options: List[Dict]
    ) -> Dict:
        """
        Analisa opcoes de compra para um usuario especifico
        """
        user_available_cash = user.available_cash
        
        capacity = self.smart_choice.calculate_payment_capacity(
            monthly_income=user.monthly_income,
            fixed_expenses=user.fixed_expenses,
            safety_margin_pct=user.safety_margin,
            current_commitments=user.total_committed
        )
        
        user_monthly_capacity = Decimal(str(capacity['safe_installment_capacity']))
        
        result = self.smart_choice.smart_choice(
            user_available_cash=user_available_cash,
            user_monthly_capacity=user_monthly_capacity,
            store_options=store_options
        )
        
        result['user_capacity'] = capacity
        
        return result
    
    def get_project_suggestions(
        self,
        project
    ) -> Dict:
        """
        Obtem sugestoes For You para um projeto
        """
        existing_items = [item.name for item in project.items.all()]
        
        return self.for_you.get_suggestions_for_project(
            project_name=project.name,
            project_type=project.project_type,
            existing_items=existing_items
        )
