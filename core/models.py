from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal
import re


class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'Usuário'),
        ('partner', 'Parceiro'),
        ('admin', 'Administrador'),
    ]
    
    corporate_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="ID corporativo (ex: PRT-FAGUAS, ADM-01)"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    monthly_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Orçamento mensal do usuário"
    )
    monthly_income = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Renda mensal do usuário"
    )
    fixed_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Gastos fixos mensais (aluguel, contas, etc)"
    )
    safety_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Margem de segurança em porcentagem (padrão 10%)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def safety_margin_value(self):
        return (self.monthly_income * self.safety_margin) / Decimal('100')
    
    @property
    def free_cash_flow(self):
        return self.monthly_income - self.fixed_expenses - self.safety_margin_value
    
    @property
    def total_committed(self):
        from django.db.models import Sum
        total = Decimal('0')
        for project in self.projects.all():
            total += project.total_monthly_installment
        return total
    
    @property
    def available_cash(self):
        return self.free_cash_flow - self.total_committed
    
    @property
    def commitment_percentage(self):
        if self.free_cash_flow > 0:
            return (self.total_committed / self.free_cash_flow) * 100
        return Decimal('0')
    
    @property
    def is_over_committed(self):
        return self.total_committed > self.free_cash_flow
    
    def save(self, *args, **kwargs):
        if self.role == 'partner' and not self.slug:
            base_slug = slugify(self.username)
            self.slug = base_slug
            counter = 1
            while User.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    @property
    def is_partner(self):
        return self.role == 'partner'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'
    
    @property
    def is_regular_user(self):
        return self.role == 'user'
    
    @classmethod
    def detect_id_type(cls, identifier):
        if re.match(r'^PRT-[A-Z0-9]+$', identifier, re.IGNORECASE):
            return 'partner'
        elif re.match(r'^ADM-\d+$', identifier, re.IGNORECASE):
            return 'admin'
        return 'regular'
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'


class PartnerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='partner_profile'
    )
    amazon_tag = models.CharField(max_length=100, blank=True, null=True)
    kabum_id = models.CharField(max_length=100, blank=True, null=True)
    terabyte_code = models.CharField(max_length=100, blank=True, null=True)
    aliexpress_id = models.CharField(max_length=100, blank=True, null=True)
    pichau_id = models.CharField(max_length=100, blank=True, null=True)
    
    total_clicks = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_tag_for_store(self, store_name):
        store_mapping = {
            'amazon': self.amazon_tag,
            'kabum': self.kabum_id,
            'terabyte': self.terabyte_code,
            'aliexpress': self.aliexpress_id,
            'pichau': self.pichau_id,
        }
        return store_mapping.get(store_name.lower())
    
    class Meta:
        verbose_name = 'Perfil de Parceiro'
        verbose_name_plural = 'Perfis de Parceiros'


class AdminSettings(models.Model):
    amazon_tag = models.CharField(max_length=100, default='admin-tag-21')
    kabum_id = models.CharField(max_length=100, default='admin-kabum')
    terabyte_code = models.CharField(max_length=100, default='admin-terabyte')
    aliexpress_id = models.CharField(max_length=100, default='admin-aliexpress')
    pichau_id = models.CharField(max_length=100, default='admin-pichau')
    
    class Meta:
        verbose_name = 'Configuração Admin'
        verbose_name_plural = 'Configurações Admin'
    
    @classmethod
    def get_fallback_tag(cls, store_name):
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        store_mapping = {
            'amazon': settings_obj.amazon_tag,
            'kabum': settings_obj.kabum_id,
            'terabyte': settings_obj.terabyte_code,
            'aliexpress': settings_obj.aliexpress_id,
            'pichau': settings_obj.pichau_id,
        }
        return store_mapping.get(store_name.lower())


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Criação'),
        ('update', 'Atualização'),
        ('delete', 'Exclusão'),
        ('view', 'Visualização'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='audit_logs'
    )
    admin_id = models.CharField(max_length=50, blank=True, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    object_repr = models.CharField(max_length=255, blank=True, null=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.admin_id or self.user} - {self.action} - {self.timestamp}"


class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('pc', 'PC / Setup Gamer'),
        ('casa', 'Casa / Decoração'),
        ('eletro', 'Eletrodomésticos'),
        ('moveis', 'Móveis'),
        ('eletronicos', 'Eletrônicos'),
        ('outro', 'Outro'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='projects'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, default='outro')
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_cash_price(self):
        return sum((item.total_cash_price for item in self.items.all()), Decimal('0'))
    
    @property
    def total_installment_price(self):
        return sum((item.total_installment_price for item in self.items.all()), Decimal('0'))
    
    @property
    def total_monthly_installment(self):
        return sum((item.monthly_installment for item in self.items.all()), Decimal('0'))
    
    @property
    def savings_if_cash(self):
        return self.total_installment_price - self.total_cash_price
    
    @property
    def is_over_budget(self):
        return self.budget > 0 and self.total_monthly_installment > self.budget
    
    @property
    def budget_percentage_used(self):
        if self.budget > 0:
            return (self.total_monthly_installment / self.budget) * 100
        return Decimal('0')
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    class Meta:
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']


class Item(models.Model):
    STORE_CHOICES = [
        ('kabum', 'Kabum'),
        ('amazon', 'Amazon'),
        ('pichau', 'Pichau'),
        ('terabyte', 'Terabyte'),
        ('aliexpress', 'AliExpress'),
        ('mercadolivre', 'Mercado Livre'),
        ('magazineluiza', 'Magazine Luiza'),
        ('outro', 'Outro'),
    ]
    
    CATEGORY_CHOICES = [
        ('gpu', 'Placa de Vídeo'),
        ('cpu', 'Processador'),
        ('ram', 'Memória RAM'),
        ('ssd', 'SSD/HD'),
        ('motherboard', 'Placa Mãe'),
        ('psu', 'Fonte'),
        ('case', 'Gabinete'),
        ('cooler', 'Cooler'),
        ('monitor', 'Monitor'),
        ('keyboard', 'Teclado'),
        ('mouse', 'Mouse'),
        ('headset', 'Headset'),
        ('chair', 'Cadeira'),
        ('desk', 'Mesa'),
        ('sofa', 'Sofá'),
        ('tv', 'TV'),
        ('geladeira', 'Geladeira'),
        ('fogao', 'Fogão'),
        ('maquinalavar', 'Máquina de Lavar'),
        ('outro', 'Outro'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='outro')
    store = models.CharField(max_length=100, choices=STORE_CHOICES, default='kabum')
    link = models.URLField(max_length=500, blank=True, null=True)
    cash_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    installment_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    installment_count = models.PositiveIntegerField(default=1)
    interest_free = models.BooleanField(default=True, help_text="Parcelamento sem juros")
    image_url = models.URLField(max_length=500, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_cash_price(self):
        return self.cash_price * self.quantity
    
    @property
    def total_installment_price(self):
        return self.installment_price * self.quantity
    
    @property
    def monthly_installment(self):
        if self.installment_count > 0:
            return (self.installment_price * self.quantity) / self.installment_count
        return Decimal('0')
    
    @property
    def savings_if_cash(self):
        return self.total_installment_price - self.total_cash_price
    
    @property
    def has_savings(self):
        return self.savings_if_cash > 0
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Itens'
        ordering = ['-created_at']


class PartnerClick(models.Model):
    partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='partner_clicks'
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.URLField(max_length=500, blank=True, null=True)
    store = models.CharField(max_length=50, blank=True)
    converted = models.BooleanField(default=False)
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Click de Parceiro'
        verbose_name_plural = 'Clicks de Parceiros'
        ordering = ['-created_at']
