from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from catalogue.models import Categorie, Ouvrage, Exemplaire
from loans.models import Emprunt
from reservations.models import Reservation
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed demo data: users, categories, ouvrages, exemplaires, sample loan/reservation'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin12345', role=User.ROLE_ADMIN)
        if not User.objects.filter(username='biblio').exists():
            User.objects.create_user('biblio', 'biblio@example.com', 'biblio12345', role=User.ROLE_BIBLIO)
        if not User.objects.filter(username='lecteur').exists():
            User.objects.create_user('lecteur', 'lecteur@example.com', 'lecteur12345', role=User.ROLE_LECTEUR)

        # categories
        c1, _ = Categorie.objects.get_or_create(nom='Littérature')
        c2, _ = Categorie.objects.get_or_create(nom='Science')

        # ouvrages
        o1, _ = Ouvrage.objects.get_or_create(isbn='9782070368220', defaults={'titre': 'L Étranger', 'auteur': 'Albert Camus', 'sujet': 'Roman', 'categorie': c1, 'editeur': 'Gallimard', 'annee_publication': 1942, 'resume': 'Un roman...'})
        o2, _ = Ouvrage.objects.get_or_create(isbn='9782130404500', defaults={'titre': 'Physique pour tous', 'auteur': 'Dupont', 'sujet': 'Physique', 'categorie': c2, 'editeur': 'Dunod', 'annee_publication': 2010, 'resume': 'Livre de physique.'})

        # exemplaires
        Exemplaire.objects.get_or_create(ouvrage=o1, code='LIT-1')
        Exemplaire.objects.get_or_create(ouvrage=o1, code='LIT-2')
        Exemplaire.objects.get_or_create(ouvrage=o2, code='SCI-1')

        # sample loan
        lecteur = User.objects.get(username='lecteur')
        ex = Exemplaire.objects.filter(ouvrage=o2).first()
        if ex and not Emprunt.objects.filter(exemplaire=ex, lecteur=lecteur).exists():
            emprunt = Emprunt.objects.create(exemplaire=ex, lecteur=lecteur, bibliothecaire=User.objects.get(username='biblio'))
            emprunt.date_retour_prevue = timezone.now() + timezone.timedelta(days=14)
            emprunt.save()

        # sample reservation
        Reservation.objects.get_or_create(ouvrage=o1, lecteur=lecteur)

        self.stdout.write(self.style.SUCCESS('Demo data created'))
