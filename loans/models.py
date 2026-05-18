from django.db import models
from django.conf import settings
from django.utils import timezone


class LoanRequest(models.Model):
	STATUS_PENDING = 'en_attente'
	STATUS_APPROVED = 'approuve'
	STATUS_REJECTED = 'rejete'
	STATUS_CANCELLED = 'annulee'

	STATUS_CHOICES = [
		(STATUS_PENDING, 'En attente'),
		(STATUS_APPROVED, 'Approuvé'),
		(STATUS_REJECTED, 'Refusé'),
		(STATUS_CANCELLED, 'Annulée'),
	]

	ouvrage = models.ForeignKey('catalogue.Ouvrage', on_delete=models.CASCADE)
	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	date_demande = models.DateTimeField(default=timezone.now)
	date_debut_souhaite = models.DateField(null=True, blank=True)
	date_fin_souhaite = models.DateField(null=True, blank=True)
	statut = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
	commentaire = models.TextField(blank=True)

	class Meta:
		ordering = ['-date_demande']

	def __str__(self):
		return f"Demande {self.ouvrage.titre} — {self.lecteur.username} ({self.get_statut_display()})"


class Emprunt(models.Model):
	STAT_EN_COURS = 'en_cours'
	STAT_RET = 'retourne'
	STAT_RETARD = 'en_retard'

	STATUT_CHOICES = [
		(STAT_EN_COURS, 'En cours'),
		(STAT_RET, 'Retourné'),
		(STAT_RETARD, 'En retard'),
	]

	exemplaire = models.ForeignKey('catalogue.Exemplaire', on_delete=models.PROTECT)
	lecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emprunts')
	bibliothecaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='emprunts_geres')
	date_emprunt = models.DateTimeField(default=timezone.now)
	date_retour_prevue = models.DateTimeField(null=True, blank=True)
	date_retour_effective = models.DateTimeField(null=True, blank=True)
	statut = models.CharField(max_length=32, choices=STATUT_CHOICES, default=STAT_EN_COURS)

	FINE_PER_DAY = 2  # MAD

	def calculate_fine(self):
		if not self.date_retour_effective and self.date_retour_prevue:
			delta = timezone.now() - self.date_retour_prevue
			days = max(0, delta.days)
			return days * self.FINE_PER_DAY
		if self.date_retour_effective and self.date_retour_prevue:
			delta = self.date_retour_effective - self.date_retour_prevue
			days = max(0, delta.days)
			return days * self.FINE_PER_DAY
		return 0

	@property
	def days_remaining(self):
		if self.date_retour_prevue and self.statut == self.STAT_EN_COURS:
			return (self.date_retour_prevue.date() - timezone.localdate()).days
		return 0

	@property
	def overdue_days(self):
		if self.date_retour_prevue and self.statut in [self.STAT_EN_COURS, self.STAT_RETARD] and timezone.now() > self.date_retour_prevue:
			return (timezone.localdate() - self.date_retour_prevue.date()).days
		return 0

	@property
	def is_overdue(self):
		return self.date_retour_prevue and timezone.now() > self.date_retour_prevue and self.statut in [self.STAT_EN_COURS, self.STAT_RETARD]

	@property
	def is_active(self):
		return self.statut in [self.STAT_EN_COURS, self.STAT_RETARD] and not self.date_retour_effective

	@property
	def can_be_returned(self):
		return self.is_active

	def __str__(self):
		return f"{self.exemplaire} — {self.lecteur.username} ({self.statut})"

