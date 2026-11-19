from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Utilisateur


class UtilisateurForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        required=False,
        widget=forms.PasswordInput,
        help_text="Laisser vide pour conserver le mot de passe actuel.",
    )

    class Meta:
        model = Utilisateur
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
            "role",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        self.creation = kwargs.pop("creation", False)
        super().__init__(*args, **kwargs)
        if self.creation:
            self.fields["mot_de_passe"].required = True
            self.fields["mot_de_passe"].help_text = "Obligatoire à la création."

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        mot_de_passe = self.cleaned_data.get("mot_de_passe")
        if mot_de_passe:
            utilisateur.set_password(mot_de_passe)
        if commit:
            utilisateur.save()
        return utilisateur


class CreationUtilisateurForm(UserCreationForm):
    class Meta:
        model = Utilisateur
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
            "role",
            "is_active",
        ]
