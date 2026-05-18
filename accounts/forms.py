from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label='Mot de passe',
        help_text='Laissez vide pour conserver le mot de passe existant.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_password = self.instance.password if self.instance and self.instance.pk else None

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'telephone',
            'adresse',
            'role',
            'statut_compte',
            'is_suspended',
            'password',
        )
        labels = {
            'username': 'Nom utilisateur',
            'email': 'Adresse email',
            'first_name': 'Prenom',
            'last_name': 'Nom',
            'telephone': 'Telephone',
            'adresse': 'Adresse',
            'role': 'Role',
            'statut_compte': 'Statut du compte',
            'is_suspended': 'Compte suspendu',
        }
        help_texts = {
            'role': 'Choisissez l acces de l utilisateur.',
            'statut_compte': 'Definissez si le compte est actif ou bloque.',
            'is_suspended': 'Cochez pour suspendre temporairement l acces.',
            'password': 'Nouveau mot de passe optionnel.',
        }

    def clean(self):
        cleaned_data = super().clean()
        statut_compte = cleaned_data.get('statut_compte')
        is_suspended = cleaned_data.get('is_suspended')
        password = cleaned_data.get('password')

        if not self.instance.pk and not password:
            self.add_error('password', 'Le mot de passe est obligatoire pour creer un compte.')

        if is_suspended and statut_compte == User.STATUT_ACTIF:
            cleaned_data['statut_compte'] = User.STATUT_SUSPENDU
        elif statut_compte and statut_compte != User.STATUT_ACTIF:
            cleaned_data['is_suspended'] = True

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.statut_compte = self.cleaned_data.get('statut_compte', user.statut_compte)
        user.is_suspended = self.cleaned_data.get('is_suspended', user.is_suspended)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        elif self._original_password:
            user.password = self._original_password
        if commit:
            user.save()
        return user


class RegisterForm(UserForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label='Mot de passe',
        help_text='Choisissez un mot de passe securise.',
    )

    class Meta(UserForm.Meta):
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'telephone',
            'adresse',
            'password',
        )
        labels = {
            'username': 'Nom utilisateur',
            'email': 'Adresse email',
            'first_name': 'Prenom',
            'last_name': 'Nom',
            'telephone': 'Telephone',
            'adresse': 'Adresse',
            'password': 'Mot de passe',
        }
        help_texts = {
            'password': 'Choisissez un mot de passe securise.',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_LECTEUR
        user.statut_compte = User.STATUT_ACTIF
        user.is_suspended = False
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'telephone',
            'adresse',
        )
        labels = {
            'username': 'Nom utilisateur',
            'email': 'Adresse email',
            'first_name': 'Prenom',
            'last_name': 'Nom',
            'telephone': 'Telephone',
            'adresse': 'Adresse',
        }
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 4}),
        }
