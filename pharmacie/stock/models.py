from django.conf import settings
from django.db import models
from django.utils import timezone


class LotStock(models.Model):
    medicament = models.ForeignKey(
        "medicaments.Medicament",
        on_delete=models.PROTECT,
        related_name="lots",
        verbose_name="Médicament",
    )
    numero_lot = models.CharField("Numéro de lot", max_length=100)
    date_peremption = models.DateField("Date de péremption")
    quantite = models.PositiveIntegerField("Quantité en stock", default=0)
    date_reception = models.DateTimeField("Date de réception", auto_now_add=True)
    bloque = models.BooleanField(
        "Bloqué", default=False, help_text="Un lot bloqué ne peut pas être vendu."
    )

    class Meta:
        verbose_name = "Lot de stock"
        verbose_name_plural = "Lots de stock"
        ordering = ["date_peremption", "numero_lot"]
        unique_together = [("medicament", "numero_lot")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantite__gte=0),
                name="lot_quantite_positive",
            )
        ]

    def __str__(self):
        return f"{self.medicament.nom} - lot {self.numero_lot}"

    @property
    def est_perime(self):
        return self.date_peremption < timezone.localdate()

    @property
    def est_delivrable(self):
        return not self.bloque and not self.est_perime and self.quantite > 0

    @property
    def jours_avant_peremption(self):
        return (self.date_peremption - timezone.localdate()).days


class MouvementStock(models.Model):
    class Type(models.TextChoices):
        ENTREE = "ENTREE", "Entrée (réception)"
        SORTIE = "SORTIE", "Sortie (vente)"
        RETOUR = "RETOUR", "Retour en stock"
        CORRECTION = "CORRECTION", "Correction d'inventaire"

    medicament = models.ForeignKey(
        "medicaments.Medicament",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name="Médicament",
    )
    lot = models.ForeignKey(
        LotStock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements",
        verbose_name="Lot",
    )
    type = models.CharField("Type", max_length=15, choices=Type.choices)
    quantite = models.IntegerField(
        "Quantité", help_text="Positive pour une entrée, négative pour une sortie."
    )
    motif = models.CharField("Motif", max_length=255, blank=True)
    reference = models.CharField("Référence", max_length=100, blank=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements_stock",
        verbose_name="Utilisateur",
    )
    date = models.DateTimeField("Date", auto_now_add=True)

    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        ordering = ["-date", "-id"]

    def __str__(self):
        signe = "+" if self.quantite >= 0 else ""
        return f"{self.date:%d/%m/%Y} {self.medicament.nom} {signe}{self.quantite}"
