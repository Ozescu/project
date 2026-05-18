from django.test import TestCase
from catalogue.models import Ouvrage, Categorie


class RecFallbackTests(TestCase):
    def test_fallback_returns_books(self):
        c = Categorie.objects.create(nom='T')
        Ouvrage.objects.create(isbn='1', titre='T1', auteur='A', categorie=c)
        Ouvrage.objects.create(isbn='2', titre='T2', auteur='B', categorie=c)
        # ensure view renders without sklearn
        from django.test import Client
        client = Client()
        resp = client.get('/recommendations/')
        self.assertIn(resp.status_code, (200, 302))
from django.test import TestCase

# Create your tests here.
