from django import forms
from .models import Categorie, Ouvrage, Exemplaire


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ('nom',)
        labels = {
            'nom': 'Nom de la catégorie',
        }


class OuvrageForm(forms.ModelForm):
    class Meta:
        model = Ouvrage
        fields = ('isbn', 'titre', 'auteur', 'sujet', 'categorie', 'editeur', 'annee_publication', 'resume', 'couverture')
        labels = {
            'isbn': 'ISBN',
            'titre': 'Titre',
            'auteur': 'Auteur',
            'sujet': 'Sujet',
            'categorie': 'Catégorie',
            'editeur': 'Éditeur',
            'annee_publication': 'Année de publication',
            'resume': 'Résumé',
            'couverture': 'Couverture',
        }
        help_texts = {
            'isbn': 'Entrez le numéro ISBN ou l’identifiant du livre.',
            'annee_publication': 'Format : AAAA.',
            'resume': 'Rédigez un bref résumé pour aider les lecteurs à comprendre le livre.',
            'couverture': 'Téléchargez une image de couverture au format JPG ou PNG.',
        }
        widgets = {
            'resume': forms.Textarea(attrs={'rows': 5}),
        }


class ExemplaireForm(forms.ModelForm):
    class Meta:
        model = Exemplaire
        fields = ('ouvrage', 'code', 'status')
        labels = {
            'ouvrage': 'Ouvrage',
            'code': 'Code de l’exemplaire',
            'status': 'Statut',
        }
