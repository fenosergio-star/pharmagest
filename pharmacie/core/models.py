from django.conf import settings
from django.db import models


class JournalAudit(models.Model):
    """Trace les opérations sensibles réalisées dans l'application."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions_audit",
        verbose_name="Utilisateur",
    )
    action = models.CharField("Action", max_length=150)
    modele = models.CharField("Objet concerné", max_length=100, blank=True)
    objet_id = models.CharField("Identifiant de l'objet", max_length=50, blank=True)
    details = models.TextField("Détails", blank=True)
    adresse_ip = models.GenericIPAddressField("Adresse IP", null=True, blank=True)
    date = models.DateTimeField("Date", auto_now_add=True)

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-date"]

    def __str__(self):
        auteur = self.utilisateur or "Système"
        return f"{self.date:%d/%m/%Y %H:%M} - {auteur} - {self.action}"
