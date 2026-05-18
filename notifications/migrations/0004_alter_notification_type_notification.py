from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('notifications', '0003_notification_ouvrage_and_return_type'),
	]

	operations = [
		migrations.AlterField(
			model_name='notification',
			name='type_notification',
			field=models.CharField(choices=[('rappel', 'Rappel'), ('retard', 'Retard'), ('disponibilite', 'Disponibilite'), ('reservation', 'Demande'), ('emprunt', 'Emprunt'), ('refus', 'Refus'), ('retour', 'Retour')], max_length=32),
		),
	]
