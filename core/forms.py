from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, PartnerProfile, Project, Item


class UnifiedLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            'placeholder': 'Email, usuário ou ID corporativo (PRT-XXX / ADM-XX)',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            'placeholder': 'Sua senha',
        })
    )


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            'placeholder': 'Crie uma senha',
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            'placeholder': 'Confirme a senha',
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'monthly_budget']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'Escolha um usuário',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'seu@email.com',
            }),
            'monthly_budget': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': '2000.00',
                'step': '0.01',
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('As senhas não coincidem.')
        return cleaned_data


class PartnerTagsForm(forms.ModelForm):
    class Meta:
        model = PartnerProfile
        fields = ['amazon_tag', 'kabum_id', 'terabyte_code', 'aliexpress_id', 'pichau_id']
        widgets = {
            'amazon_tag': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
                'placeholder': 'ex: minha-tag-21'
            }),
            'kabum_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
                'placeholder': 'ex: kabum123'
            }),
            'terabyte_code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
                'placeholder': 'ex: terabyte456'
            }),
            'aliexpress_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
                'placeholder': 'ex: aliexpress789'
            }),
            'pichau_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
                'placeholder': 'ex: pichau000'
            }),
        }
        labels = {
            'amazon_tag': 'Amazon Tag',
            'kabum_id': 'Kabum ID',
            'terabyte_code': 'Terabyte Code',
            'aliexpress_id': 'AliExpress ID',
            'pichau_id': 'Pichau ID',
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'project_type', 'description', 'budget']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'Nome do projeto',
            }),
            'project_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'rows': 3,
                'placeholder': 'Descrição opcional',
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'placeholder': 'Orçamento mensal para parcelas',
            }),
        }
        labels = {
            'name': 'Nome do Projeto',
            'project_type': 'Tipo do Projeto',
            'description': 'Descrição',
            'budget': 'Orçamento Mensal (R$)',
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'store', 'link', 'cash_price', 'installment_price', 'installment_count', 'interest_free', 'quantity', 'image_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'Nome do produto',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            }),
            'store': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
            }),
            'link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'https://...',
            }),
            'cash_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'placeholder': 'Preço à vista (Pix)',
            }),
            'installment_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'placeholder': 'Preço parcelado total',
            }),
            'installment_count': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'min': '1',
                'placeholder': 'Número de parcelas',
            }),
            'interest_free': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'min': '1',
                'value': '1',
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'placeholder': 'URL da imagem (opcional)',
            }),
        }
        labels = {
            'name': 'Nome do Produto',
            'category': 'Categoria',
            'store': 'Loja',
            'link': 'Link do Produto',
            'cash_price': 'Preço à Vista (R$)',
            'installment_price': 'Preço Parcelado Total (R$)',
            'installment_count': 'Número de Parcelas',
            'interest_free': 'Sem Juros',
            'quantity': 'Quantidade',
            'image_url': 'URL da Imagem',
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['monthly_income', 'fixed_expenses', 'safety_margin']
        widgets = {
            'monthly_income': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'placeholder': 'Sua renda mensal',
            }),
            'fixed_expenses': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'placeholder': 'Gastos fixos (aluguel, contas, etc)',
            }),
            'safety_margin': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400',
                'step': '0.01',
                'min': '0',
                'max': '50',
                'placeholder': 'Margem de segurança (%)',
            }),
        }
        labels = {
            'monthly_income': 'Renda Mensal (R$)',
            'fixed_expenses': 'Gastos Fixos (R$)',
            'safety_margin': 'Margem de Segurança (%)',
        }
