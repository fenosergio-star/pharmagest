from django import forms

from .models import LigneVente, Vente


class CheckoutForm(forms.Form):
    client = forms.ModelChoiceField(
        label="Client",
        queryset=None,
        required=False,
        empty_label="Vente comptoir (client non identifié)",
    )
    mode_paiement = forms.ChoiceField(
        label="Mode de paiement", choices=Vente.ModePaiement.choices
    )
    reference_paiement = forms.CharField(
        label="Référence du paiement",
        required=False,
        help_text="Numéro de transaction Mobile Money ou carte, si applicable.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from clients.models import Client

        self.fields["client"].queryset = Client.objects.filter(actif=True).order_by("nom")


class RetourForm(forms.Form):
    ligne_vente = forms.ModelChoiceField(
        label="Ligne de vente", queryset=LigneVente.objects.none()
    )
    quantite = forms.IntegerField(label="Quantité retournée", min_value=1)
    motif = forms.CharField(
        label="Motif du retour", widget=forms.Textarea(attrs={"rows": 2})
    )
    remise_en_stock = forms.BooleanField(
        label="Remettre le produit en stock",
        required=False,
        initial=True,
        help_text="Décocher si le produit ne peut pas être remis en vente.",
    )

    def __init__(self, *args, vente=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vente is not None:
            self.fields["ligne_vente"].queryset = vente.lignes.select_related(
                "medicament"
            )
