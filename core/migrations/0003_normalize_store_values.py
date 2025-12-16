from django.db import migrations

def normalize_store_values(apps, schema_editor):
    Item = apps.get_model('core', 'Item')
    store_mapping = {
        'Kabum': 'kabum',
        'kabum': 'kabum',
        'Amazon': 'amazon',
        'amazon': 'amazon',
        'Pichau': 'pichau',
        'pichau': 'pichau',
        'Terabyte': 'terabyte',
        'terabyte': 'terabyte',
        'AliExpress': 'aliexpress',
        'Aliexpress': 'aliexpress',
        'aliexpress': 'aliexpress',
        'Outro': 'outro',
        'outro': 'outro',
    }
    
    for item in Item.objects.all():
        new_store = store_mapping.get(item.store, 'outro')
        if item.store != new_store:
            item.store = new_store
            item.save(update_fields=['store'])

def reverse_normalize(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_item_store'),
    ]

    operations = [
        migrations.RunPython(normalize_store_values, reverse_normalize),
    ]
