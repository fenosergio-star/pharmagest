from django import forms


class CorrectionStockForm(forms.Form):
    nouvelle_quantite = forms.IntegerField(
        label="Quantité réelle constatée", min_value=0
    )
    motif = forms.CharField(
        label="Motif de la correction",
        max_length=255,
        initial="Inventaire physique",
    )


class BlocageLotForm(forms.Form):
    motif = forms.CharField(label="Motif du blocage / déblocage", max_length=255)
