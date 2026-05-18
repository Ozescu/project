from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
	TYPE_RAPPEL = 'rappel'
	TYPE_RETARD = 'retard'
	TYPE_DISPO = 'disponibilite'
	TYPE_RESERVATION = 'reservation'
	TYPE_EMPRUNT = 'emprunt'
	TYPE_REFUSAL = 'refus'
	TYPE_RETOUR = 'retour'

	TYPE_CHOICES = [
		(TYPE_RAPPEL, 'Rappel'),
		(TYPE_RETARD, 'Retard'),
		(TYPE_DISPO, 'Disponibilite'),
		(TYPE_RESERVATION, 'Demande'),
		(TYPE_EMPRUNT, 'Emprunt'),
		(TYPE_REFUSAL, 'Refus'),
		(TYPE_RETOUR, 'Retour'),
	]

	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	ouvrage = models.ForeignKey('catalogue.Ouvrage', on_delete=models.SET_NULL, null=True, blank=True)
	type_notification = models.CharField(max_length=32, choices=TYPE_CHOICES)
	message = models.TextField()
	date_envoi = models.DateTimeField(default=timezone.now)
	lu = models.BooleanField(default=False)

	class Meta:
		ordering = ['-date_envoi']

	def __str__(self):
		return f"{self.lecteur.username} - {self.type_notification}"
