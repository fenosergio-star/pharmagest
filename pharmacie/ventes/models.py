from django.conf import settings
from django.db import models

from core.utils import generer_numero


class Vente(models.Model):
    class Statut(models.TextChoices):
        VALIDEE = "VALIDEE", "Validée"
        ANNULEE = "ANNULEE", "Annulée"

    class ModePaiement(models.TextChoices):
        ESPECES = "ESPECES", "Espèces"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        CARTE = "CARTE", "Carte bancaire"
        AUTRE = "AUTRE", "Autre"

    numero = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventes",
        verbose_name="Client",
        help_text="Laisser vide pour une vente comptoir.",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventes",
        verbose_name="Vendu par",
    )
    date_vente = models.DateTimeField("Date de vente", auto_now_add=True)
    statut = models.CharField(
        "Statut", max_length=10, choices=Statut.choices, default=Statut.VALIDEE
    )
    mode_paiement = models.CharField(
        "Mode de paiement", max_length=15, choices=ModePaiement.choices
    )

    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ["-date_vente"]

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = generer_numero(Vente, "VTE")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero

    @property
    def total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), 0)

    @property
    def montant_rembourse(self):
        return sum((retour.montant_rembourse for retour in self.retours.all()), 0)

    @property
    def net(self):
        return self.total - self.montant_rembourse

    @property
    def est_retournable(self):
        return self.statut == self.Statut.VALIDEE


class LigneVente(models.Model):
    vente = models.ForeignKey(
        Vente,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Vente",
    )
    medicament = models.ForeignKey(
        "medicaments.Medicament",
        on_delete=models.PROTECT,
        related_name="lignes_vente",
        verbose_name="Médicament",
    )
    lot = models.ForeignKey(
        "stock.LotStock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_vente",
        verbose_name="Lot",
    )
    quantite = models.PositiveIntegerField("Quantité")
    prix_unitaire = models.DecimalField(
        "Prix unitaire appliqué", max_digits=12, decimal_places=2
    )

    class Meta:
        verbose_name = "Ligne de vente"
        verbose_name_plural = "Lignes de vente"

    def __str__(self):
        return f"{self.medicament.nom} x{self.quantite}"

    @property
    def sous_total(self):
        return self.quantite * self.prix_unitaire

    @property
    def quantite_retournee(self):
        return sum((retour.quantite for retour in self.retours.all()), 0)

    @property
    def quantite_retournable(self):
        return self.quantite - self.quantite_retournee


class Paiement(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRME = "CONFIRME", "Confirmé"
        ECHOUE = "ECHOUE", "Échoué"

    vente = models.ForeignKey(
        Vente,
        on_delete=models.CASCADE,
        related_name="paiements",
        verbose_name="Vente",
    )
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=2)
    mode = models.CharField(
        "Mode", max_length=15, choices=Vente.ModePaiement.choices
    )
    statut = models.CharField(
        "Statut", max_length=12, choices=Statut.choices, default=Statut.CONFIRME
    )
    reference = models.CharField("Référence", max_length=100, blank=True)
    date = models.DateTimeField("Date", auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.vente.numero} - {self.montant}"


class RetourVente(models.Model):
    vente = models.ForeignKey(
        Vente,
        on_delete=models.PROTECT,
        related_name="retours",
        verbose_name="Vente d'origine",
    )
    ligne_vente = models.ForeignKey(
        LigneVente,
        on_delete=models.PROTECT,
        related_name="retours",
        verbose_name="Ligne de vente",
    )
    quantite = models.PositiveIntegerField("Quantité retournée")
    motif = models.TextField("Motif du retour")
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retours_vente",
        verbose_name="Enregistré par",
    )
    remise_en_stock = models.BooleanField(
        "Remise en stock", default=True,
        help_text="Décocher si le produit ne peut pas être remis en vente.",
    )
    montant_rembourse = models.DecimalField(
        "Montant remboursé", max_digits=12, decimal_places=2, default=0
    )
    date = models.DateTimeField("Date", auto_now_add=True)

    class Meta:
        verbose_name = "Retour de vente"
        verbose_name_plural = "Retours de vente"
        ordering = ["-date"]

    def __str__(self):
        return f"Retour {self.vente.numero} - {self.ligne_vente.medicament.nom}"
