from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import PartnerProfile
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria usuários de teste (Admin, Parceiro, User) com credenciais fixas e dados compatíveis com o Model customizado.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando criação de usuários de teste...')

        # LISTA DE DADOS DOS USUÁRIOS
        users_config = [
            {
                # SUPER ADMIN
                'username': 'admin_master',
                'password': 'Admin@123',
                'email': 'admin@upgrade.com',
                'role': 'admin',
                'corporate_id': 'ADM-MASTER-01',
                'monthly_income': '15000.00',
                'monthly_budget': '5000.00',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'Master',
            },
            {
                # PARCEIRO (AFILIADO)
                'username': 'partner_alpha',
                'password': 'Partner@123',
                'email': 'partner@upgrade.com',
                'role': 'partner',
                'corporate_id': 'PRT-TEST-ALPHA',
                'monthly_income': '10000.00',
                'monthly_budget': '3000.00',
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Parceiro',
                'last_name': 'Alpha',
            },
            {
                # USUÁRIO COMUM
                'username': 'user_client',
                'password': 'User@123',
                'email': 'client@upgrade.com',
                'role': 'user',
                'corporate_id': 'USR-CLIENT-007',
                'monthly_income': '5000.00',
                'monthly_budget': '2000.00',
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Usuario',
                'last_name': 'Cliente',
            }
        ]

        for data in users_config:
            # Separa a senha e flags especiais para tratar depois
            password = data.pop('password')
            username = data['username']
            
            # Converte strings de dinheiro para Decimal (Obrigatório para seu Model)
            data['monthly_income'] = Decimal(data['monthly_income'])
            data['monthly_budget'] = Decimal(data['monthly_budget'])

            # update_or_create: Se o user já existe, atualiza os dados. Se não, cria.
            user, created = User.objects.update_or_create(
                username=username,
                defaults=data
            )

            # Define a senha corretamente (faz o hash)
            user.set_password(password)
            user.save()

            action = "CRIADO" if created else "ATUALIZADO"
            self.stdout.write(self.style.SUCCESS(f'[{action}] Usuário: {username} ({data["role"]})'))

            # LÓGICA ESPECIAL PARA PARCEIRO
            # Se for parceiro, garante que existe o PartnerProfile
            if data['role'] == 'partner':
                PartnerProfile.objects.get_or_create(user=user)
                self.stdout.write(f'   -> Perfil de Parceiro verificado/criado.')

        self.stdout.write(self.style.SUCCESS('\n--- CONCLUÍDO ---'))
        self.stdout.write('Credenciais para Login:')
        self.stdout.write('1. Admin:   admin_master  / Admin@123')
        self.stdout.write('2. Parceiro: partner_alpha / Partner@123')
        self.stdout.write('3. User:     user_client   / User@123')
