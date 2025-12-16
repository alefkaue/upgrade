from django.core.management.base import BaseCommand
from core.models import User, PartnerProfile
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create test users for development/testing purposes'

    def handle(self, *args, **options):
        users_data = [
            {
                'corporate_id': 'ADM-MASTER-01',
                'username': 'adm_master',
                'email': 'admin@upgrade.com',
                'password': 'Sup3r_S3cur3_P@ssw0rd!',
                'role': 'admin',
                'first_name': 'Admin',
                'last_name': 'Master',
                'monthly_income': Decimal('15000.00'),
                'monthly_budget': Decimal('5000.00'),
            },
            {
                'corporate_id': 'PRT-TEST-ALPHA',
                'username': 'partner_alpha',
                'email': 'partner@upgrade.com',
                'password': 'P@rtner_M0ney_2025',
                'role': 'partner',
                'first_name': 'Parceiro',
                'last_name': 'Alpha',
                'slug': 'partner-alpha',
                'monthly_income': Decimal('10000.00'),
                'monthly_budget': Decimal('3000.00'),
            },
            {
                'corporate_id': 'USR-CLIENT-007',
                'username': 'user_client',
                'email': 'user@upgrade.com',
                'password': 'My_Dr3am_S3tup_Go!',
                'role': 'user',
                'first_name': 'Usuario',
                'last_name': 'Cliente',
                'monthly_income': Decimal('8000.00'),
                'monthly_budget': Decimal('2000.00'),
            },
        ]

        for user_data in users_data:
            password = user_data.pop('password')
            corporate_id = user_data.get('corporate_id')
            
            user, created = User.objects.get_or_create(
                corporate_id=corporate_id,
                defaults=user_data
            )
            
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user.username} (ID: {corporate_id})')
                )
                
                if user.role == 'partner':
                    PartnerProfile.objects.get_or_create(user=user)
                    self.stdout.write(
                        self.style.SUCCESS(f'  -> Partner profile created')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists: {user.username} (ID: {corporate_id})')
                )

        self.stdout.write(self.style.SUCCESS('\nTest users setup complete!'))
        self.stdout.write('\nCredentials:')
        self.stdout.write('  Admin:    ADM-MASTER-01 / Sup3r_S3cur3_P@ssw0rd!')
        self.stdout.write('  Partner:  PRT-TEST-ALPHA / P@rtner_M0ney_2025')
        self.stdout.write('  User:     USR-CLIENT-007 / My_Dr3am_S3tup_Go!')
