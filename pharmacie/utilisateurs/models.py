from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Utilisateur de l'application avec un rôle métier."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        PHARMACIEN = "PHARMACIEN", "Pharmacien responsable"
        GESTIONNAIRE = "GESTIONNAIRE", "Gestionnaire de stock"
        CAISSIER = "CAISSIER", "Caissier"
        RESPONSABLE = "RESPONSABLE", "Responsable de gestion"

    role = models.CharField(
        "Rôle", max_length=20, choices=Role.choices, default=Role.CAISSIER
    )
    telephone = models.CharField("Téléphone", max_length=30, blank=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def est_administrateur(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def a_un_role(self, *roles):
        return self.est_administrateur or self.role in roles
