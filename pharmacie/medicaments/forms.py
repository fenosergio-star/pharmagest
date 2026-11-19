from django import forms

from .models import Categorie, Medicament


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ["nom", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MedicamentForm(forms.ModelForm):
    class Meta:
        model = Medicament
        fields = [
            "nom",
            "denomination_generique",
            "categorie",
            "forme",
            "dosage",
            "laboratoire",
            "code_barres",
            "photo",
            "prix_achat",
            "prix_vente",
            "seuil_alerte",
            "statut",
        ]
        widgets = {
            "prix_achat": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "prix_vente": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean_code_barres(self):
        code = (self.cleaned_data.get("code_barres") or "").strip()
        return code or None

    def clean(self):
        donnees = super().clean()
        prix_achat = donnees.get("prix_achat")
        prix_vente = donnees.get("prix_vente")
        if prix_achat is not None and prix_vente is not None and prix_vente < prix_achat:
            self.add_error(
                "prix_vente",
                "Le prix de vente ne peut pas être inférieur au prix d'achat.",
            )
        return donnees
