# Generated manually to add an explicit refused reservation status.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_alter_reservation_statut'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='statut',
            field=models.CharField(
                choices=[
                    ('active', 'En attente'),
                    ('honoree', 'Acceptée'),
                    ('refusee', 'Refusée'),
                    ('expiree', 'Terminée'),
                    ('annulee', 'Annulée'),
                ],
                default='active',
                max_length=32,
            ),
        ),
    ]
