from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Categorie, Exemplaire, Ouvrage
from loans import services
from .models import Sanction


class SanctionActionTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_user('sanction_admin', 'admin@example.com', 'pw', role=User.ROLE_ADMIN)
		self.reader = User.objects.create_user('sanction_reader', 'reader@example.com', 'pw')
		category = Categorie.objects.create(nom='Essai')
		book = Ouvrage.objects.create(isbn='sanction-1', titre='Livre sanction', auteur='Auteur', categorie=category)
		copy = Exemplaire.objects.create(ouvrage=book, code='SAN-1')
		loan = services.create_loan_from_copy(copy, self.reader)
		self.sanction = Sanction.objects.create(
			lecteur=self.reader,
			emprunt=loan,
			type_sanction=Sanction.TYPE_AMENDE,
			montant=10,
			statut='active',
		)

	def test_admin_can_resolve_sanction(self):
		self.client.force_login(self.admin)

		response = self.client.post(reverse('sanctions:resolve', args=[self.sanction.pk]))
		self.sanction.refresh_from_db()

		self.assertRedirects(response, reverse('sanctions:mine'))
		self.assertEqual(self.sanction.statut, 'resolue')
		self.assertIsNotNone(self.sanction.date_fin)
