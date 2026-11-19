from django import forms

from .models import Fournisseur


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = [
            "nom",
            "adresse",
            "telephone",
            "email",
            "numero_fiscal",
            "contact_principal",
            "actif",
        ]
        widgets = {"adresse": forms.Textarea(attrs={"rows": 3})}
