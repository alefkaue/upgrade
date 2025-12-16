"""
Financial Sniper - Serviços de Análise Financeira
Módulo com funções de cálculo para importação, parcelamento e comparação de preços
"""

import requests
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple, List
from datetime import datetime


class DollarQuoteService:
    """Serviço para obter cotação do dólar em tempo real"""
    
    AWESOME_API_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
    
    @classmethod
    def get_current_rate(cls) -> Tuple[Decimal, str]:
        """
        Obtém a cotação atual do dólar.
        Retorna tupla (cotação, data_hora)
        """
        try:
            response = requests.get(cls.AWESOME_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'USDBRL' in data:
                rate = Decimal(data['USDBRL']['bid'])
                timestamp = data['USDBRL'].get('create_date', datetime.now().isoformat())
                return rate, timestamp
        except Exception as e:
            pass
        
        return Decimal('5.50'), datetime.now().isoformat()


class ImportTaxCalculator:
    """
    Calculadora de taxas de importação brasileiras
    Aplica regras do Remessa Conforme e taxas tradicionais
    """
    
    ICMS_RATE = Decimal('0.17')
    IMPORT_TAX_ABOVE_50 = Decimal('0.60')
    IMPORT_TAX_BELOW_50 = Decimal('0.20')
    THRESHOLD_USD = Decimal('50.00')
    
    @classmethod
    def calculate_import_cost(
        cls,
        price_usd: Decimal,
        shipping_usd: Decimal = Decimal('0'),
        is_remessa_conforme: bool = True
    ) -> Dict:
        """
        Calcula o custo total de importação incluindo taxas
        
        Args:
            price_usd: Preço do produto em dólares
            shipping_usd: Custo de frete em dólares
            is_remessa_conforme: Se a loja participa do programa Remessa Conforme
            
        Returns:
            Dict com breakdown completo dos custos
        """
        dollar_rate, rate_timestamp = DollarQuoteService.get_current_rate()
        
        total_usd = price_usd + shipping_usd
        base_brl = total_usd * dollar_rate
        
        if is_remessa_conforme:
            if total_usd <= cls.THRESHOLD_USD:
                import_tax = base_brl * cls.IMPORT_TAX_BELOW_50
            else:
                import_tax = base_brl * cls.IMPORT_TAX_ABOVE_50
        else:
            import_tax = base_brl * cls.IMPORT_TAX_ABOVE_50
        
        subtotal_with_tax = base_brl + import_tax
        icms = subtotal_with_tax * cls.ICMS_RATE
        
        total_brl = subtotal_with_tax + icms
        
        return {
            'price_usd': float(price_usd),
            'shipping_usd': float(shipping_usd),
            'total_usd': float(total_usd),
            'dollar_rate': float(dollar_rate),
            'rate_timestamp': rate_timestamp,
            'base_brl': float(base_brl.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'import_tax_rate': float(cls.IMPORT_TAX_BELOW_50 if total_usd <= cls.THRESHOLD_USD and is_remessa_conforme else cls.IMPORT_TAX_ABOVE_50),
            'import_tax_brl': float(import_tax.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'icms_rate': float(cls.ICMS_RATE),
            'icms_brl': float(icms.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'total_brl': float(total_brl.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'is_remessa_conforme': is_remessa_conforme,
        }
    
    @classmethod
    def compare_import_vs_national(
        cls,
        import_price_usd: Decimal,
        national_price_brl: Decimal,
        shipping_usd: Decimal = Decimal('0'),
        is_remessa_conforme: bool = True
    ) -> Dict:
        """
        Compara custo de importação vs compra nacional
        
        Returns:
            Dict com análise comparativa e recomendação
        """
        import_calc = cls.calculate_import_cost(
            import_price_usd, 
            shipping_usd, 
            is_remessa_conforme
        )
        
        import_total = Decimal(str(import_calc['total_brl']))
        national_total = national_price_brl
        
        difference = national_total - import_total
        percentage_diff = ((national_total - import_total) / national_total * 100) if national_total > 0 else Decimal('0')
        
        if difference > 0:
            recommendation = 'import'
            savings = difference
            recommendation_text = f"Importar é mais barato. Economia de R$ {float(savings):.2f} ({float(percentage_diff):.1f}%)"
        elif difference < 0:
            recommendation = 'national'
            savings = abs(difference)
            recommendation_text = f"Comprar no Brasil é mais barato. Economia de R$ {float(savings):.2f} ({float(abs(percentage_diff)):.1f}%)"
        else:
            recommendation = 'equal'
            savings = Decimal('0')
            recommendation_text = "Preços equivalentes. Considere o prazo de entrega."
        
        return {
            'import_analysis': import_calc,
            'national_price_brl': float(national_price_brl),
            'price_difference': float(difference.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'percentage_difference': float(percentage_diff.quantize(Decimal('0.1'), ROUND_HALF_UP)),
            'recommendation': recommendation,
            'recommendation_text': recommendation_text,
            'savings': float(savings.quantize(Decimal('0.01'), ROUND_HALF_UP)),
        }


class InstallmentAnalyzer:
    """
    Analisador de parcelamento vs pagamento à vista
    Considera inflação e valor do dinheiro no tempo
    """
    
    ANNUAL_INFLATION_RATE = Decimal('0.045')
    MONTHLY_INFLATION_RATE = (Decimal('1') + ANNUAL_INFLATION_RATE) ** (Decimal('1') / Decimal('12')) - Decimal('1')
    
    @classmethod
    def calculate_installment_value(
        cls,
        total_price: Decimal,
        num_installments: int,
        interest_rate: Decimal = Decimal('0')
    ) -> Dict:
        """
        Calcula valor de parcela e custo total com juros
        
        Args:
            total_price: Preço total do produto
            num_installments: Número de parcelas
            interest_rate: Taxa de juros mensal (ex: 0.0199 para 1.99%)
            
        Returns:
            Dict com valores calculados
        """
        if interest_rate > 0:
            if interest_rate == Decimal('1'):
                installment_value = total_price / num_installments
            else:
                rate = interest_rate
                pmt = total_price * (rate * (1 + rate) ** num_installments) / ((1 + rate) ** num_installments - 1)
                installment_value = pmt
            total_with_interest = installment_value * num_installments
        else:
            installment_value = total_price / num_installments
            total_with_interest = total_price
        
        interest_paid = total_with_interest - total_price
        
        return {
            'original_price': float(total_price),
            'num_installments': num_installments,
            'interest_rate_monthly': float(interest_rate * 100),
            'installment_value': float(installment_value.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'total_with_interest': float(total_with_interest.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'interest_paid': float(interest_paid.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'interest_free': interest_rate == 0,
        }
    
    @classmethod
    def compare_cash_vs_installment(
        cls,
        cash_price: Decimal,
        installment_price: Decimal,
        num_installments: int,
        interest_free: bool = True
    ) -> Dict:
        """
        Compara pagamento à vista vs parcelado considerando valor do dinheiro no tempo
        
        Returns:
            Dict com análise completa e recomendação
        """
        cash_discount = installment_price - cash_price
        cash_discount_pct = (cash_discount / installment_price * 100) if installment_price > 0 else Decimal('0')
        
        monthly_installment = installment_price / num_installments
        
        present_value = Decimal('0')
        monthly_rate = cls.MONTHLY_INFLATION_RATE
        
        for month in range(1, num_installments + 1):
            pv_factor = Decimal('1') / ((Decimal('1') + monthly_rate) ** month)
            present_value += monthly_installment * pv_factor
        
        inflation_savings = installment_price - present_value
        
        net_benefit_installment = inflation_savings - cash_discount
        
        if cash_discount_pct >= Decimal('10'):
            recommendation = 'cash'
            recommendation_text = f"Pague à vista. Desconto de {float(cash_discount_pct):.1f}% supera ganho com inflação."
            financial_benefit = cash_discount
        elif net_benefit_installment > Decimal('50') and interest_free:
            recommendation = 'installment'
            recommendation_text = f"Parcele sem juros. A inflação trabalha a seu favor, economia real de R$ {float(net_benefit_installment):.2f}."
            financial_benefit = net_benefit_installment
        elif not interest_free:
            recommendation = 'cash'
            recommendation_text = f"Pague à vista para evitar juros. Economia de R$ {float(cash_discount):.2f}."
            financial_benefit = cash_discount
        else:
            recommendation = 'neutral'
            recommendation_text = "Diferença mínima. Escolha conforme seu fluxo de caixa."
            financial_benefit = Decimal('0')
        
        return {
            'cash_price': float(cash_price),
            'installment_price': float(installment_price),
            'num_installments': num_installments,
            'monthly_installment': float(monthly_installment.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'cash_discount': float(cash_discount.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'cash_discount_percentage': float(cash_discount_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
            'present_value_installments': float(present_value.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'inflation_savings': float(inflation_savings.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'net_benefit_installment': float(net_benefit_installment.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'interest_free': interest_free,
            'recommendation': recommendation,
            'recommendation_text': recommendation_text,
            'financial_benefit': float(financial_benefit.quantize(Decimal('0.01'), ROUND_HALF_UP)) if isinstance(financial_benefit, Decimal) else float(financial_benefit),
            'annual_inflation_rate': float(cls.ANNUAL_INFLATION_RATE * 100),
        }


class PriceExtractor:
    """Utilitário para extrair e limpar preços de strings"""
    
    @classmethod
    def extract_price(cls, price_string: str) -> Optional[Decimal]:
        """
        Extrai valor numérico de uma string de preço
        
        Exemplos:
            "R$ 1.299,00" -> Decimal('1299.00')
            "US$ 49.99" -> Decimal('49.99')
            "1299.99" -> Decimal('1299.99')
        """
        if not price_string:
            return None
            
        cleaned = re.sub(r'[R$US\s]', '', str(price_string))
        
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            if cleaned.count(',') == 1 and len(cleaned.split(',')[1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        try:
            return Decimal(cleaned)
        except:
            return None
    
    @classmethod
    def format_brl(cls, value: Decimal) -> str:
        """Formata valor para Real brasileiro"""
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    @classmethod
    def format_usd(cls, value: Decimal) -> str:
        """Formata valor para Dólar americano"""
        return f"US$ {float(value):,.2f}"


class IncomeProjectAnalyzer:
    """
    Analisador de Renda vs Projeto
    Cruza dados financeiros do usuário com custos do projeto
    para recomendar a melhor estratégia de compra
    """
    
    @classmethod
    def analyze_affordability(
        cls,
        monthly_income: Decimal,
        fixed_expenses: Decimal,
        item_price_cash: Decimal,
        item_price_installment: Decimal,
        installment_count: int,
        current_commitments: Decimal = Decimal('0'),
        safety_margin_pct: Decimal = Decimal('10')
    ) -> Dict:
        """
        Analisa se um item cabe no orçamento do usuário
        e qual a melhor estratégia de compra
        """
        safety_margin = (monthly_income * safety_margin_pct) / Decimal('100')
        free_cash_flow = monthly_income - fixed_expenses - safety_margin
        available_budget = free_cash_flow - current_commitments
        
        monthly_installment = item_price_installment / installment_count if installment_count > 0 else item_price_installment
        
        can_afford_cash = available_budget >= item_price_cash
        can_afford_installment = available_budget >= monthly_installment
        
        commitment_with_item = current_commitments + monthly_installment
        new_commitment_pct = (commitment_with_item / free_cash_flow * 100) if free_cash_flow > 0 else Decimal('999')
        
        months_to_save_cash = int((item_price_cash / available_budget).quantize(Decimal('1'), ROUND_HALF_UP)) if available_budget > 0 else 999
        
        cash_discount = item_price_installment - item_price_cash
        cash_discount_pct = (cash_discount / item_price_installment * 100) if item_price_installment > 0 else Decimal('0')
        
        installment_as_income_pct = (monthly_installment / monthly_income * 100) if monthly_income > 0 else Decimal('999')
        
        if can_afford_cash and cash_discount_pct >= Decimal('10'):
            recommendation = 'cash_immediate'
            strategy = 'À vista imediato'
            reason = f"Você tem fluxo de caixa e o desconto de {float(cash_discount_pct):.1f}% vale a pena. Economia de R$ {float(cash_discount):.2f}."
            risk_level = 'low'
        elif can_afford_installment and new_commitment_pct <= Decimal('30'):
            recommendation = 'installment_safe'
            strategy = f'Parcelado em {installment_count}x'
            reason = f"Parcela de R$ {float(monthly_installment):.2f} compromete apenas {float(installment_as_income_pct):.1f}% da sua renda. Seguro."
            risk_level = 'low'
        elif can_afford_installment and new_commitment_pct <= Decimal('50'):
            recommendation = 'installment_moderate'
            strategy = f'Parcelado em {installment_count}x (atenção)'
            reason = f"Parcela cabe no orçamento, mas você ficará com {float(new_commitment_pct):.1f}% comprometido. Considere esperar."
            risk_level = 'medium'
        elif can_afford_installment:
            recommendation = 'installment_risky'
            strategy = f'Parcelado em {installment_count}x (arriscado)'
            reason = f"A parcela cabe, mas comprometeria {float(new_commitment_pct):.1f}% do seu fluxo livre. Alto risco financeiro."
            risk_level = 'high'
        elif months_to_save_cash <= 6:
            recommendation = 'save_first'
            strategy = f'Economizar por {months_to_save_cash} meses'
            reason = f"Não cabe agora, mas economizando R$ {float(available_budget):.2f}/mês você compra à vista em {months_to_save_cash} meses."
            risk_level = 'low'
        else:
            recommendation = 'not_affordable'
            strategy = 'Fora do orçamento atual'
            reason = f"Este item está acima do seu poder de compra. Considere uma alternativa mais barata ou aumente sua renda."
            risk_level = 'critical'
        
        return {
            'monthly_income': float(monthly_income),
            'fixed_expenses': float(fixed_expenses),
            'free_cash_flow': float(free_cash_flow),
            'available_budget': float(available_budget),
            'current_commitments': float(current_commitments),
            'item_price_cash': float(item_price_cash),
            'item_price_installment': float(item_price_installment),
            'installment_count': installment_count,
            'monthly_installment': float(monthly_installment.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'can_afford_cash': can_afford_cash,
            'can_afford_installment': can_afford_installment,
            'new_commitment_pct': float(new_commitment_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
            'installment_as_income_pct': float(installment_as_income_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
            'cash_discount': float(cash_discount.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            'cash_discount_pct': float(cash_discount_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
            'months_to_save_cash': months_to_save_cash,
            'recommendation': recommendation,
            'strategy': strategy,
            'reason': reason,
            'risk_level': risk_level,
        }
    
    @classmethod
    def compare_store_options(
        cls,
        user_available_budget: Decimal,
        options: List[Dict]
    ) -> Dict:
        """
        Compara múltiplas opções de lojas e retorna a melhor para o perfil do usuário
        """
        if not options:
            return {'error': 'Nenhuma opção fornecida'}
        
        analyzed_options = []
        
        for opt in options:
            price_cash = Decimal(str(opt.get('price_cash', 0)))
            price_inst = Decimal(str(opt.get('price_installment', price_cash)))
            inst_count = opt.get('installment_count', 1)
            interest_free = opt.get('interest_free', True)
            
            monthly_inst = price_inst / inst_count if inst_count > 0 else price_inst
            installment_fits = monthly_inst <= user_available_budget
            
            cash_discount = price_inst - price_cash
            cash_discount_pct = (cash_discount / price_inst * 100) if price_inst > 0 else Decimal('0')
            
            if installment_fits and interest_free and inst_count >= 12:
                score = 100 - float(monthly_inst / user_available_budget * 30) if user_available_budget > 0 else 50
            elif installment_fits and interest_free:
                score = 80 - float(monthly_inst / user_available_budget * 20) if user_available_budget > 0 else 40
            elif price_cash <= user_available_budget:
                score = 70 + float(cash_discount_pct)
            elif installment_fits:
                score = 50 - float(monthly_inst / user_available_budget * 20) if user_available_budget > 0 else 30
            else:
                score = 10
            
            analyzed_options.append({
                'store': opt.get('store', 'Desconhecida'),
                'price_cash': float(price_cash),
                'price_installment': float(price_inst),
                'installment_count': inst_count,
                'monthly_installment': float(monthly_inst.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                'interest_free': interest_free,
                'installment_fits_budget': installment_fits,
                'cash_discount': float(cash_discount.quantize(Decimal('0.01'), ROUND_HALF_UP)),
                'cash_discount_pct': float(cash_discount_pct.quantize(Decimal('0.1'), ROUND_HALF_UP)),
                'score': round(score, 1),
                'url': opt.get('url', ''),
            })
        
        analyzed_options.sort(key=lambda x: x['score'], reverse=True)
        
        best = analyzed_options[0]
        
        if best['installment_fits_budget'] and best['interest_free']:
            recommendation_text = f"Recomendo a {best['store']}. Parcela em {best['installment_count']}x sem juros de R$ {best['monthly_installment']:.2f}, que cabe no seu orçamento."
        elif best['price_cash'] <= float(user_available_budget):
            recommendation_text = f"Recomendo a {best['store']} à vista por R$ {best['price_cash']:.2f}. Economia de R$ {best['cash_discount']:.2f}."
        else:
            recommendation_text = f"A melhor opção é {best['store']}, mas avalie se cabe no seu orçamento atual."
        
        return {
            'best_option': best,
            'all_options': analyzed_options,
            'recommendation_text': recommendation_text,
            'user_budget': float(user_available_budget),
        }
    
    @classmethod
    def suggest_max_installments(
        cls,
        item_price: Decimal,
        user_available_budget: Decimal,
        max_installments: int = 24
    ) -> Dict:
        """
        Sugere o número ideal de parcelas para um item baseado no orçamento do usuário
        """
        if user_available_budget <= 0:
            return {
                'suggestion': 'Sem orçamento disponível',
                'min_installments': None,
                'comfortable_installments': None,
            }
        
        min_installments = int((item_price / user_available_budget).quantize(Decimal('1'), ROUND_HALF_UP))
        
        if min_installments <= 0:
            min_installments = 1
        
        comfortable_pct = Decimal('0.30')
        comfortable_payment = user_available_budget * comfortable_pct
        comfortable_installments = int((item_price / comfortable_payment).quantize(Decimal('1'), ROUND_HALF_UP)) if comfortable_payment > 0 else max_installments
        
        if comfortable_installments <= 0:
            comfortable_installments = 1
        
        if min_installments > max_installments:
            suggestion = f"Este item está acima do seu orçamento. Precisaria de {min_installments}x mas o máximo comum é {max_installments}x."
        elif comfortable_installments <= 12:
            suggestion = f"Ideal: {comfortable_installments}x (parcela confortável de R$ {float(item_price / comfortable_installments):.2f})"
        else:
            suggestion = f"Mínimo: {min_installments}x | Confortável: {min(comfortable_installments, max_installments)}x"
        
        return {
            'suggestion': suggestion,
            'min_installments': min_installments,
            'comfortable_installments': min(comfortable_installments, max_installments),
            'item_price': float(item_price),
            'user_budget': float(user_available_budget),
        }


class FinancialSniper:
    """
    Classe principal que integra todos os serviços financeiros
    Ponto de entrada para o chatbot
    """
    
    def __init__(self):
        self.import_calculator = ImportTaxCalculator()
        self.installment_analyzer = InstallmentAnalyzer()
        self.price_extractor = PriceExtractor()
        self.dollar_service = DollarQuoteService()
        self.income_analyzer = IncomeProjectAnalyzer()
    
    def analyze_affordability(
        self,
        user,
        item_price_cash: float,
        item_price_installment: float,
        installment_count: int
    ) -> Dict:
        """
        Analisa se um item cabe no orçamento de um usuário específico
        """
        return self.income_analyzer.analyze_affordability(
            Decimal(str(user.monthly_income)),
            Decimal(str(user.fixed_expenses)),
            Decimal(str(item_price_cash)),
            Decimal(str(item_price_installment)),
            installment_count,
            Decimal(str(user.total_committed)),
            Decimal(str(user.safety_margin))
        )
    
    def compare_stores_for_user(
        self,
        user,
        options: List[Dict]
    ) -> Dict:
        """
        Compara opções de lojas para um usuário específico
        """
        return self.income_analyzer.compare_store_options(
            Decimal(str(user.available_cash)),
            options
        )
    
    def suggest_installments_for_user(
        self,
        user,
        item_price: float
    ) -> Dict:
        """
        Sugere parcelamento ideal para um usuário
        """
        return self.income_analyzer.suggest_max_installments(
            Decimal(str(item_price)),
            Decimal(str(user.available_cash))
        )
    
    def analyze_import(
        self,
        price_usd: float,
        shipping_usd: float = 0,
        national_price_brl: float = None,
        is_remessa_conforme: bool = True
    ) -> Dict:
        """
        Análise completa de importação
        """
        price = Decimal(str(price_usd))
        shipping = Decimal(str(shipping_usd))
        
        if national_price_brl:
            return self.import_calculator.compare_import_vs_national(
                price, 
                Decimal(str(national_price_brl)),
                shipping,
                is_remessa_conforme
            )
        else:
            return self.import_calculator.calculate_import_cost(
                price, 
                shipping, 
                is_remessa_conforme
            )
    
    def analyze_payment(
        self,
        cash_price: float,
        installment_price: float,
        num_installments: int,
        interest_free: bool = True
    ) -> Dict:
        """
        Análise completa de forma de pagamento
        """
        return self.installment_analyzer.compare_cash_vs_installment(
            Decimal(str(cash_price)),
            Decimal(str(installment_price)),
            num_installments,
            interest_free
        )
    
    def get_dollar_quote(self) -> Dict:
        """
        Obtém cotação atual do dólar
        """
        rate, timestamp = self.dollar_service.get_current_rate()
        return {
            'rate': float(rate),
            'timestamp': timestamp,
            'formatted': f"R$ {float(rate):.4f}"
        }
    
    def parse_price(self, price_string: str) -> Optional[float]:
        """
        Extrai preço de uma string
        """
        result = self.price_extractor.extract_price(price_string)
        return float(result) if result else None
