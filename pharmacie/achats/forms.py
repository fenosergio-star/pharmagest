from django import forms
from django.forms import inlineformset_factory

from .models import CommandeAchat, LigneAchat


class CommandeAchatForm(forms.ModelForm):
    class Meta:
        model = CommandeAchat
        fields = ["fournisseur", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fournisseur"].queryset = self.fields["fournisseur"].queryset.filter(
            actif=True
        )


class LigneAchatForm(forms.ModelForm):
    class Meta:
        model = LigneAchat
        fields = ["medicament", "quantite", "prix_achat"]
        widgets = {
            "quantite": forms.NumberInput(attrs={"min": "1"}),
            "prix_achat": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from medicaments.models import Medicament

        self.fields["medicament"].queryset = Medicament.objects.filter(
            statut=Medicament.Statut.ACTIF
        )


LigneAchatFormSet = inlineformset_factory(
    CommandeAchat,
    LigneAchat,
    form=LigneAchatForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class ReceptionForm(forms.Form):
    """Formulaire dynamique : une ligne par médicament restant à recevoir."""

    notes = forms.CharField(
        label="Notes de réception", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
