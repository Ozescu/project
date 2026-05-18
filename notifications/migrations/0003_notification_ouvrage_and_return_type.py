from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('catalogue', '0002_favorite'),
		('notifications', '0002_alter_notification_type_notification'),
	]

	operations = [
		migrations.AddField(
			model_name='notification',
			name='ouvrage',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='catalogue.ouvrage'),
		),
		migrations.AlterField(
			model_name='notification',
			name='type_notification',
			field=models.CharField(choices=[('rappel', 'Rappel'), ('retard', 'Retard'), ('disponibilite', 'Disponibilite'), ('reservation', 'Demande'), ('emprunt', 'Emprunt'), ('refus', 'Refus'), ('retour', 'Retour')], max_length=32),
		),
	]
