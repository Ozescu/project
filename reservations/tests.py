from django.test import TestCase
from catalogue.models import Ouvrage, Categorie, Exemplaire
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Reservation


class ReservationTests(TestCase):
    def test_queue_position(self):
        User = get_user_model()
        c = Categorie.objects.create(nom='T')
        o = Ouvrage.objects.create(isbn='x1', titre='t', auteur='a', categorie=c)
        u1 = User.objects.create_user('u1', 'u1@example.com', 'pw')
        u2 = User.objects.create_user('u2', 'u2@example.com', 'pw')
        r1 = Reservation.objects.create(ouvrage=o, lecteur=u1)
        r2 = Reservation.objects.create(ouvrage=o, lecteur=u2)
        self.assertEqual(r1.position_file, 1)
        self.assertEqual(r2.position_file, 2)

    def test_admin_can_reject_reservation(self):
        User = get_user_model()
        admin = User.objects.create_user('reservation_admin', 'admin@example.com', 'pw', role=User.ROLE_ADMIN)
        reader = User.objects.create_user('reservation_reader', 'reader@example.com', 'pw')
        c = Categorie.objects.create(nom='Histoire')
        o = Ouvrage.objects.create(isbn='r1', titre='reservation', auteur='a', categorie=c)
        reservation = Reservation.objects.create(ouvrage=o, lecteur=reader)

        self.client.force_login(admin)
        response = self.client.post(reverse('reservations:reject', args=[reservation.pk]))
        reservation.refresh_from_db()

        self.assertRedirects(response, reverse('reservations:my_reservations'))
        self.assertEqual(reservation.statut, Reservation.STATUS_REFUSEE)
