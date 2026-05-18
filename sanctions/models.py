from django.db import models
from django.conf import settings
from django.utils import timezone


class Sanction(models.Model):
	TYPE_AMENDE = 'amende'
	TYPE_SUSP = 'suspension'
	TYPE_BLOC = 'blocage'

	TYPE_CHOICES = [
		(TYPE_AMENDE, 'Amende'),
		(TYPE_SUSP, 'Suspension'),
		(TYPE_BLOC, 'Blocage'),
	]

	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	emprunt = models.ForeignKey('loans.Emprunt', on_delete=models.SET_NULL, null=True, blank=True)
	type_sanction = models.CharField(max_length=32, choices=TYPE_CHOICES)
	montant = models.DecimalField(max_digits=8, decimal_places=2, default=0)
	date_debut = models.DateTimeField(default=timezone.now)
	date_fin = models.DateTimeField(null=True, blank=True)
	statut = models.CharField(max_length=32, default='active')

	class Meta:
		ordering = ['-date_debut']

	def __str__(self):
		return f"{self.lecteur.username} - {self.type_sanction}"

