from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogue.models import Categorie, Exemplaire, Ouvrage
from loans import services
from notifications.models import Notification
from reservations.models import Reservation
from sanctions.models import Sanction


class AdminDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user('admin_dash', 'admin@example.com', 'pw', role=User.ROLE_ADMIN)
        self.reader = User.objects.create_user('reader_dash', 'reader@example.com', 'pw')
        self.category = Categorie.objects.create(nom='Science')
        self.book = Ouvrage.objects.create(isbn='dash-1', titre='Livre dashboard', auteur='Auteur', categorie=self.category)
        self.copy = Exemplaire.objects.create(ouvrage=self.book, code='DASH-1')
        self.loan = services.create_loan_from_copy(self.copy, self.reader)
        self.loan.date_retour_prevue = timezone.now() - timezone.timedelta(days=1)
        self.loan.save(update_fields=['date_retour_prevue'])
        Reservation.objects.create(ouvrage=self.book, lecteur=self.reader)
        Notification.objects.create(
            lecteur=self.reader,
            ouvrage=self.book,
            type_notification=Notification.TYPE_RETARD,
            message='Retard test',
        )
        Sanction.objects.create(
            lecteur=self.reader,
            emprunt=self.loan,
            type_sanction=Sanction.TYPE_AMENDE,
            montant=10,
            statut='active',
        )

    def test_admin_dashboard_renders_core_sections(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tableau de bord administrateur')
        self.assertContains(response, 'Activité récente')
        self.assertContains(response, 'Alertes opérationnelles')
        self.assertContains(response, 'Ouvrages')
        self.assertContains(response, 'Exemplaires')
        self.assertContains(response, 'Notifications importantes')
        self.assertNotContains(response, 'Top favoris')
        self.assertNotContains(response, 'Livres populaires')
        self.assertNotContains(response, 'Top catégories')
        self.assertNotContains(response, 'Actions utiles')
        self.assertNotContains(response, 'Sanctions actives')

    def test_admin_support_pages_render(self):
        self.client.force_login(self.admin)

        for route, expected in [
            ('dashboard:notification_settings', 'Paramètres notifications'),
            ('dashboard:sanction_settings', 'Paramètres sanctions'),
            ('dashboard:system_reports', 'Rapports système'),
        ]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected)

    def test_reader_cannot_open_admin_dashboard(self):
        self.client.force_login(self.reader)

        response = self.client.get(reverse('dashboard:admin'))

        self.assertContains(response, 'refus', status_code=200)
