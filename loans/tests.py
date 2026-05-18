from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from catalogue.models import Ouvrage, Categorie, Exemplaire
from notifications.models import Notification
from reservations.models import Reservation

from . import services
from .models import Emprunt


class LoanTests(TestCase):
    def test_fine_calculation(self):
        User = get_user_model()
        c = Categorie.objects.create(nom='T')
        o = Ouvrage.objects.create(isbn='i', titre='t', auteur='a', categorie=c)
        ex = Exemplaire.objects.create(ouvrage=o, code='x')
        u = User.objects.create_user('u', 'u@example.com', 'pw')
        e = Emprunt.objects.create(exemplaire=ex, lecteur=u)
        e.date_retour_prevue = timezone.now() - timezone.timedelta(days=3)
        e.save()
        self.assertTrue(e.calculate_fine() >= 6)


class ReturnWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('reader', 'reader@example.com', 'pw')
        self.category = Categorie.objects.create(nom='Science')
        self.book = Ouvrage.objects.create(isbn='12345', titre='Livre test', auteur='Auteur', categorie=self.category)
        self.exemplar = Exemplaire.objects.create(ouvrage=self.book, code='EX1')
        self.loan = services.create_loan_from_copy(self.exemplar, self.user)

    def test_reader_can_return_active_loan(self):
        fine = services.process_return(self.loan)
        self.loan.refresh_from_db()
        self.exemplar.refresh_from_db()

        self.assertEqual(self.loan.statut, Emprunt.STAT_RET)
        self.assertIsNotNone(self.loan.date_retour_effective)
        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_DISP)
        self.assertEqual(fine, 0)
        self.assertTrue(
            Notification.objects.filter(
                lecteur=self.user,
                type_notification=Notification.TYPE_RETOUR,
                ouvrage=self.book,
            ).exists()
        )

    def test_reader_can_return_active_loan_via_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('loans:return', args=[self.loan.pk]), follow=True)
        self.loan.refresh_from_db()
        self.exemplar.refresh_from_db()

        self.assertRedirects(response, reverse('loans:list'))
        self.assertEqual(self.loan.statut, Emprunt.STAT_RET)
        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_DISP)
        self.assertTrue(
            Notification.objects.filter(
                lecteur=self.user,
                type_notification=Notification.TYPE_RETOUR,
                ouvrage=self.book,
            ).exists()
        )

    def test_return_overdue_loan_clears_overdue_status(self):
        self.loan.date_retour_prevue = timezone.now() - timezone.timedelta(days=2)
        self.loan.statut = Emprunt.STAT_RETARD
        self.loan.save(update_fields=['date_retour_prevue', 'statut'])
        self.exemplar.status = Exemplaire.STATUS_RET
        self.exemplar.save(update_fields=['status'])

        fine = services.process_return(self.loan)
        self.loan.refresh_from_db()
        self.exemplar.refresh_from_db()

        self.assertEqual(self.loan.statut, Emprunt.STAT_RET)
        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_DISP)
        self.assertTrue(fine > 0)
        self.assertTrue(
            Notification.objects.filter(
                lecteur=self.user,
                type_notification=Notification.TYPE_RETOUR,
                ouvrage=self.book,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                lecteur=self.user,
                type_notification=Notification.TYPE_RETARD,
                ouvrage=self.book,
            ).exists()
        )

    def test_refresh_overdue_keeps_loan_status_in_progress(self):
        self.loan.date_retour_prevue = timezone.now() - timezone.timedelta(days=2)
        self.loan.save(update_fields=['date_retour_prevue'])

        services.refresh_overdue_loans()
        self.loan.refresh_from_db()
        self.exemplar.refresh_from_db()

        self.assertEqual(self.loan.statut, Emprunt.STAT_EN_COURS)
        self.assertIsNone(self.loan.date_retour_effective)
        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_RET)

    def test_librarian_can_return_loan(self):
        User = get_user_model()
        librarian = User.objects.create_user('librarian', 'lib@example.com', 'pw')
        librarian.role = User.ROLE_BIBLIO
        librarian.save()
        
        self.client.force_login(librarian)
        response = self.client.post(reverse('loans:return', args=[self.loan.pk]), follow=True)
        self.loan.refresh_from_db()
        self.exemplar.refresh_from_db()

        self.assertRedirects(response, reverse('loans:list'))
        self.assertEqual(self.loan.statut, Emprunt.STAT_RET)
        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_DISP)
        self.assertTrue(
            Notification.objects.filter(
                lecteur=self.user,
                type_notification=Notification.TYPE_RETOUR,
                ouvrage=self.book,
            ).exists()
        )

    def test_cannot_double_return_loan(self):
        services.process_return(self.loan)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.statut, Emprunt.STAT_RET)
        self.assertIsNotNone(self.loan.date_retour_effective)
        
        with self.assertRaises(ValueError) as context:
            services.process_return(self.loan)
        self.assertIn('deja cloture', str(context.exception))

    def test_return_does_not_create_automatic_loan_for_next_reservation(self):
        User = get_user_model()
        waiting_reader = User.objects.create_user('waiting', 'waiting@example.com', 'pw')
        Reservation.objects.create(ouvrage=self.book, lecteur=waiting_reader)

        services.process_return(self.loan)
        self.exemplar.refresh_from_db()

        self.assertEqual(self.exemplar.status, Exemplaire.STATUS_DISP)
        self.assertEqual(Emprunt.objects.filter(lecteur=waiting_reader, exemplaire__ouvrage=self.book).count(), 0)
        self.assertTrue(
            Notification.objects.filter(
                lecteur=waiting_reader,
                type_notification=Notification.TYPE_DISPO,
                ouvrage=self.book,
            ).exists()
        )

    def test_reader_list_separates_active_and_returned_without_return_button_on_history(self):
        services.process_return(self.loan)
        self.client.force_login(self.user)

        response = self.client.get(reverse('loans:list'))

        self.assertContains(response, 'Historique des emprunts')
        self.assertContains(response, 'Aucun emprunt actif.')
        self.assertNotContains(response, 'Retourner le livre')
