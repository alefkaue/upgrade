from django.core.management.base import BaseCommand
from core.models import User, PartnerProfile, AdminSettings, Product


class Command(BaseCommand):
    help = 'Create demo users for testing'

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@sistema.com',
                'corporate_id': 'ADM-01',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Administrador',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin criado: ADM-01 / admin123'))
        
        partner_user, created = User.objects.get_or_create(
            username='parceiro',
            defaults={
                'email': 'parceiro@sistema.com',
                'corporate_id': 'PRT-DEMO',
                'role': 'partner',
                'first_name': 'Parceiro Demo',
            }
        )
        if created:
            partner_user.set_password('parceiro123')
            partner_user.save()
            PartnerProfile.objects.create(
                user=partner_user,
                amazon_tag='demo-amazon-21',
                kabum_id='demo-kabum',
            )
            self.stdout.write(self.style.SUCCESS(f'Parceiro criado: PRT-DEMO / parceiro123'))
        
        normal_user, created = User.objects.get_or_create(
            username='usuario',
            defaults={
                'email': 'usuario@sistema.com',
                'role': 'user',
                'first_name': 'Usuario Teste',
                'monthly_budget': 500,
            }
        )
        if created:
            normal_user.set_password('usuario123')
            normal_user.save()
            self.stdout.write(self.style.SUCCESS(f'Usuario criado: usuario / usuario123'))
        
        AdminSettings.objects.get_or_create(pk=1)
        
        products = [
            {'name': 'RTX 4070 Super', 'store': 'Amazon', 'price': 3499.00, 'category': 'GPU', 'url': 'https://amazon.com.br/rtx4070'},
            {'name': 'Ryzen 7 5800X3D', 'store': 'Kabum', 'price': 1899.00, 'category': 'CPU', 'url': 'https://kabum.com.br/ryzen7'},
            {'name': 'SSD NVMe 1TB', 'store': 'Terabyte', 'price': 399.00, 'category': 'Storage', 'url': 'https://terabyte.com.br/ssd'},
            {'name': 'RAM DDR5 32GB', 'store': 'Pichau', 'price': 699.00, 'category': 'Memory', 'url': 'https://pichau.com.br/ram'},
            {'name': 'Monitor 27" 165Hz', 'store': 'Amazon', 'price': 1299.00, 'category': 'Monitor', 'url': 'https://amazon.com.br/monitor'},
            {'name': 'Gabinete Gamer', 'store': 'Kabum', 'price': 299.00, 'category': 'Case', 'url': 'https://kabum.com.br/gabinete'},
        ]
        
        for p in products:
            Product.objects.get_or_create(
                name=p['name'],
                defaults={
                    'store': p['store'],
                    'price': p['price'],
                    'category': p['category'],
                    'url': p['url'],
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Produtos de demo criados!'))
        self.stdout.write(self.style.SUCCESS('\\nCredenciais de teste:'))
        self.stdout.write('Admin: ADM-01 / admin123')
        self.stdout.write('Parceiro: PRT-DEMO / parceiro123')
        self.stdout.write('Usuario: usuario / usuario123')
