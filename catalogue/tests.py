from django.test import TestCase
from .models import Ouvrage, Categorie, Exemplaire


class CatalogueTests(TestCase):
    def test_availability_counts(self):
        c = Categorie.objects.create(nom='Test')
        o = Ouvrage.objects.create(isbn='123', titre='T', auteur='A', categorie=c)
        Exemplaire.objects.create(ouvrage=o, code='c1', status=Exemplaire.STATUS_DISP)
        Exemplaire.objects.create(ouvrage=o, code='c2', status=Exemplaire.STATUS_EMPR)
        self.assertEqual(o.exemplaires.count(), 2)
        self.assertEqual(o.exemplaires.filter(status=Exemplaire.STATUS_DISP).count(), 1)
from django.test import TestCase

# Create your tests here.
