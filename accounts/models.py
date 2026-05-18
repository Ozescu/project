from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
	ROLE_LECTEUR = 'lecteur'
	ROLE_BIBLIO = 'bibliothecaire'
	ROLE_ADMIN = 'administrateur'

	STATUT_ACTIF = 'actif'
	STATUT_SUSPENDU = 'suspendu'
	STATUT_BLOQUE = 'bloque'

	ROLE_CHOICES = [
		(ROLE_LECTEUR, 'Lecteur'),
		(ROLE_BIBLIO, 'Bibliothécaire'),
		(ROLE_ADMIN, 'Administrateur'),
	]

	STATUT_CHOICES = [
		(STATUT_ACTIF, 'Actif'),
		(STATUT_SUSPENDU, 'Suspendu'),
		(STATUT_BLOQUE, 'Bloqué'),
	]

	telephone = models.CharField(max_length=30, blank=True)
	adresse = models.TextField(blank=True)
	role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_LECTEUR)
	statut_compte = models.CharField(max_length=32, choices=STATUT_CHOICES, default=STATUT_ACTIF)
	is_suspended = models.BooleanField(default=False)

	class Meta:
		ordering = ['username']

	def __str__(self):
		return f"{self.username} ({self.role})"

	def is_lecteur(self):
		return self.role == self.ROLE_LECTEUR

	def is_bibliothecaire(self):
		return self.role == self.ROLE_BIBLIO

	def is_administrateur(self):
		return self.role == self.ROLE_ADMIN
