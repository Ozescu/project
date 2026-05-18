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

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
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
