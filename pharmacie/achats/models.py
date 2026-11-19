from django.conf import settings
from django.db import models
from core.utils import generer_numero


class CommandeAchat(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        COMMANDEE = "COMMANDEE", "Commandée"
        PARTIELLE = "PARTIELLE", "Partiellement réceptionnée"
        RECEPTIONNEE = "RECEPTIONNEE", "Entièrement réceptionnée"
        ANNULEE = "ANNULEE", "Annulée"

    numero = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    fournisseur = models.ForeignKey(
        "fournisseurs.Fournisseur",
        on_delete=models.PROTECT,
        related_name="commandes",
        verbose_name="Fournisseur",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commandes_achat",
        verbose_name="Créée par",
    )
    date_commande = models.DateTimeField("Date de commande", auto_now_add=True)
    statut = models.CharField(
        "Statut", max_length=15, choices=Statut.choices, default=Statut.BROUILLON
    )
    notes = models.TextField("Notes", blank=True)

    class Meta:
        verbose_name = "Commande d'achat"
        verbose_name_plural = "Commandes d'achat"
        ordering = ["-date_commande"]

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = generer_numero(CommandeAchat, "CMD")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero

    @property
    def total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), 0)

    @property
    def quantite_commandee(self):
        return sum(ligne.quantite for ligne in self.lignes.all())

    @property
    def quantite_recue(self):
        return sum(ligne.quantite_recue for ligne in self.lignes.all())

    @property
    def est_modifiable(self):
        return self.statut == self.Statut.BROUILLON

    @property
    def peut_etre_receptionnee(self):
        return self.statut in (self.Statut.COMMANDEE, self.Statut.PARTIELLE)

    @property
    def reste_a_recevoir(self):
        return sum(ligne.reste for ligne in self.lignes.all())


class LigneAchat(models.Model):
    commande = models.ForeignKey(
        CommandeAchat,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Commande",
    )
    medicament = models.ForeignKey(
        "medicaments.Medicament",
        on_delete=models.PROTECT,
        related_name="lignes_achat",
        verbose_name="Médicament",
    )
    quantite = models.PositiveIntegerField("Quantité commandée")
    prix_achat = models.DecimalField("Prix d'achat unitaire", max_digits=12, decimal_places=2)
    quantite_recue = models.PositiveIntegerField("Quantité reçue", default=0)

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"

    def __str__(self):
        return f"{self.medicament.nom} x{self.quantite}"

    @property
    def sous_total(self):
        return self.quantite * self.prix_achat

    @property
    def reste(self):
        return max(self.quantite - self.quantite_recue, 0)


class ReceptionAchat(models.Model):
    numero = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    commande = models.ForeignKey(
        CommandeAchat,
        on_delete=models.PROTECT,
        related_name="receptions",
        verbose_name="Commande",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receptions_achat",
        verbose_name="Réceptionnée par",
    )
    date_reception = models.DateTimeField("Date de réception", auto_now_add=True)
    notes = models.TextField("Notes", blank=True)

    class Meta:
        verbose_name = "Réception d'achat"
        verbose_name_plural = "Réceptions d'achat"
        ordering = ["-date_reception"]

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = generer_numero(ReceptionAchat, "REC")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero

    @property
    def montant(self):
        return sum(ligne.sous_total for ligne in self.lignes.all())


class LigneReception(models.Model):
    reception = models.ForeignKey(
        ReceptionAchat,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Réception",
    )
    ligne_achat = models.ForeignKey(
        LigneAchat,
        on_delete=models.PROTECT,
        related_name="lignes_reception",
        verbose_name="Ligne de commande",
    )
    lot = models.ForeignKey(
        "stock.LotStock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_reception",
        verbose_name="Lot créé",
    )
    numero_lot = models.CharField("Numéro de lot", max_length=100)
    date_peremption = models.DateField("Date de péremption")
    quantite = models.PositiveIntegerField("Quantité reçue")

    class Meta:
        verbose_name = "Ligne de réception"
        verbose_name_plural = "Lignes de réception"

    def __str__(self):
        return f"{self.ligne_achat.medicament.nom} x{self.quantite}"

    @property
    def sous_total(self):
        return self.quantite * self.ligne_achat.prix_achat
