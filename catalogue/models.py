from django.db import models
from django.urls import reverse
from django.conf import settings


class Categorie(models.Model):
	nom = models.CharField(max_length=200)

	def __str__(self):
		return self.nom


class Ouvrage(models.Model):
	isbn = models.CharField(max_length=32, unique=True)
	titre = models.CharField(max_length=300)
	auteur = models.CharField(max_length=200)
	sujet = models.CharField(max_length=200, blank=True)
	categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True)
	editeur = models.CharField(max_length=200, blank=True)
	annee_publication = models.IntegerField(null=True, blank=True)
	resume = models.TextField(blank=True)
	couverture = models.ImageField(upload_to='covers/', null=True, blank=True)

	def __str__(self):
		return f"{self.titre} — {self.auteur}"

	def get_absolute_url(self):
		return reverse('catalogue:detail', args=[str(self.id)])


class Exemplaire(models.Model):
	STATUS_DISP = 'disponible'
	STATUS_EMPR = 'emprunte'
	STATUS_RES = 'reserve'
	STATUS_RET = 'en_retard'
	STATUS_MAINT = 'maintenance'
	STATUS_LOST = 'perdu'

	STATUS_CHOICES = [
		(STATUS_DISP, 'Disponible'),
		(STATUS_EMPR, 'Emprunte'),
		(STATUS_RES, 'Reserve'),
		(STATUS_RET, 'En retard'),
		(STATUS_MAINT, 'Maintenance'),
		(STATUS_LOST, 'Perdu'),
	]

	ouvrage = models.ForeignKey(Ouvrage, on_delete=models.CASCADE, related_name='exemplaires')
	code = models.CharField(max_length=64, blank=True)
	status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_DISP)

	def __str__(self):
		return f"{self.ouvrage.titre} [{self.code or self.id}] - {self.status}"


class Favorite(models.Model):
	"""Favorite relationship: lecteur -> ouvrage.

	Stored here in `catalogue` to keep favourites next to books.
	"""
	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favoris')
	ouvrage = models.ForeignKey(Ouvrage, on_delete=models.CASCADE, related_name='favorited_by')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('lecteur', 'ouvrage')
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.lecteur.username} → {self.ouvrage.titre}"
