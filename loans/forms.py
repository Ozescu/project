from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalogue.models import Exemplaire


User = get_user_model()


class LoanCreateForm(forms.Form):
	lecteur = forms.ModelChoiceField(
		queryset=User.objects.none(),
		label='Lecteur',
		empty_label='Choisir un lecteur',
	)
	exemplaire = forms.ModelChoiceField(
		queryset=Exemplaire.objects.none(),
		label='Exemplaire',
		empty_label='Choisir un exemplaire disponible',
	)
	date_debut = forms.DateField(
		required=False,
		label='Date emprunt',
		widget=forms.DateInput(attrs={'type': 'date'}),
	)
	date_retour = forms.DateField(
		required=False,
		label='Date retour prevue',
		widget=forms.DateInput(attrs={'type': 'date'}),
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['lecteur'].queryset = User.objects.filter(
			role=User.ROLE_LECTEUR,
			statut_compte=User.STATUT_ACTIF,
			is_suspended=False,
		).order_by('username')
		self.fields['exemplaire'].queryset = Exemplaire.objects.filter(
			status=Exemplaire.STATUS_DISP,
		).select_related('ouvrage').order_by('ouvrage__titre', 'code')

	def clean(self):
		cleaned_data = super().clean()
		start = cleaned_data.get('date_debut') or timezone.localdate()
		due = cleaned_data.get('date_retour')
		if due and due < start:
			raise forms.ValidationError('La date de retour prevue doit etre posterieure a la date emprunt.')
		return cleaned_data
