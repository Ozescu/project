from django.db import models
from django.conf import settings
from django.utils import timezone


class Reservation(models.Model):
	STATUS_ACTIVE = 'active'
	STATUS_ANNULEE = 'annulee'
	STATUS_EXPIREE = 'expiree'
	STATUS_HONOREE = 'honoree'
	STATUS_REFUSEE = 'refusee'

	STATUS_CHOICES = [
		(STATUS_ACTIVE, 'En attente'),
		(STATUS_HONOREE, 'Acceptée'),
		(STATUS_REFUSEE, 'Refusée'),
		(STATUS_EXPIREE, 'Terminée'),
		(STATUS_ANNULEE, 'Annulée'),
	]

	ouvrage = models.ForeignKey('catalogue.Ouvrage', on_delete=models.CASCADE)
	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	date_reservation = models.DateTimeField(default=timezone.now)
	position_file = models.IntegerField(default=0)
	statut = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

	class Meta:
		ordering = ['date_reservation']

	def save(self, *args, **kwargs):
		if not self.pk:
			active = Reservation.objects.filter(ouvrage=self.ouvrage, statut=self.STATUS_ACTIVE).count()
			self.position_file = active + 1
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.ouvrage.titre} - {self.lecteur.username} ({self.position_file})"
