from django.db import models


class Client(models.Model):
    nom = models.CharField("Nom du client", max_length=200)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Adresse e-mail", blank=True)
    adresse = models.TextField("Adresse", blank=True)
    actif = models.BooleanField("Compte actif", default=True)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
