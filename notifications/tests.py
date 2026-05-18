from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Categorie, Ouvrage
from .models import Notification


class NotificationActionTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.reader = User.objects.create_user('notif_reader', 'reader@example.com', 'pw')
		category = Categorie.objects.create(nom='Roman')
		book = Ouvrage.objects.create(isbn='notif-1', titre='Livre notification', auteur='Auteur', categorie=category)
		self.notification = Notification.objects.create(
			lecteur=self.reader,
			ouvrage=book,
			type_notification=Notification.TYPE_RESERVATION,
			message='Reservation creee',
		)

	def test_reader_can_mark_notification_read(self):
		self.client.force_login(self.reader)

		response = self.client.post(reverse('notifications:mark_read', args=[self.notification.pk]))
		self.notification.refresh_from_db()

		self.assertRedirects(response, reverse('notifications:mine'))
		self.assertTrue(self.notification.lu)
