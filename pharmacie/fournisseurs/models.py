from django.db import models


class Fournisseur(models.Model):
    nom = models.CharField("Nom ou raison sociale", max_length=200)
    adresse = models.TextField("Adresse", blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Adresse e-mail", blank=True)
    numero_fiscal = models.CharField(
        "Numéro fiscal / identifiant professionnel", max_length=50, blank=True
    )
    contact_principal = models.CharField("Contact principal", max_length=150, blank=True)
    actif = models.BooleanField("Actif", default=True)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
