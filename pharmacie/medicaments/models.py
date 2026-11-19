from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Categorie(models.Model):
    nom = models.CharField("Nom", max_length=100, unique=True)
    description = models.TextField("Description", blank=True)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Medicament(models.Model):
    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        ARCHIVE = "ARCHIVE", "Archivé"

    class Forme(models.TextChoices):
        COMPRIME = "COMPRIME", "Comprimé"
        SIROP = "SIROP", "Sirop"
        GELULE = "GELULE", "Gélule"
        INJECTION = "INJECTION", "Injection"
        POMMADE = "POMMADE", "Pommade"
        SUPPOSITOIRE = "SUPPOSITOIRE", "Suppositoire"
        AUTRE = "AUTRE", "Autre"

    nom = models.CharField("Nom commercial", max_length=200)
    denomination_generique = models.CharField(
        "Dénomination générique", max_length=200, blank=True
    )
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.PROTECT,
        related_name="medicaments",
        verbose_name="Catégorie",
    )
    forme = models.CharField(
        "Forme pharmaceutique", max_length=20, choices=Forme.choices, default=Forme.COMPRIME
    )
    dosage = models.CharField("Dosage", max_length=50, blank=True)
    laboratoire = models.CharField("Laboratoire", max_length=150, blank=True)
    code_barres = models.CharField(
        "Code-barres", max_length=50, unique=True, null=True, blank=True
    )
    photo = models.ImageField("Photo", upload_to="medicaments/", blank=True, null=True)
    prix_achat = models.DecimalField(
        "Prix d'achat", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    prix_vente = models.DecimalField(
        "Prix de vente", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    seuil_alerte = models.PositiveIntegerField("Seuil d'alerte", default=10)
    statut = models.CharField(
        "Statut", max_length=10, choices=Statut.choices, default=Statut.ACTIF
    )
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Médicament"
        verbose_name_plural = "Médicaments"
        ordering = ["nom"]

    def __str__(self):
        details = " ".join(v for v in [self.dosage, self.get_forme_display()] if v)
        return f"{self.nom} ({details})" if details else self.nom

    @property
    def stock_total(self):
        return self.lots.aggregate(total=Sum("quantite"))["total"] or 0

    @property
    def stock_disponible(self):
        return (
            self.lots.filter(bloque=False, date_peremption__gte=timezone.localdate())
            .aggregate(total=Sum("quantite"))["total"]
            or 0
        )

    @property
    def est_stock_faible(self):
        return self.stock_disponible <= self.seuil_alerte

    @property
    def en_rupture(self):
        return self.stock_disponible == 0

    @property
    def marge_unitaire(self):
        return self.prix_vente - self.prix_achat

    @property
    def lots_delivrables(self):
        return self.lots.filter(
            bloque=False,
            quantite__gt=0,
            date_peremption__gte=timezone.localdate(),
        ).order_by("date_peremption")
