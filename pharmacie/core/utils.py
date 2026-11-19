"""Fonctions utilitaires partagées (numérotation, audit, IP)."""
from django.utils import timezone

from core.models import JournalAudit


def generer_numero(modele, prefixe):
    """Génère un numéro lisible et unique pour un document."""
    aujourdhui = timezone.localdate()
    base = f"{prefixe}-{aujourdhui:%Y%m%d}"
    compteur = modele.objects.filter(numero__startswith=base).count() + 1
    numero = f"{base}-{compteur:04d}"
    while modele.objects.filter(numero=numero).exists():
        compteur += 1
        numero = f"{base}-{compteur:04d}"
    return numero


def adresse_ip(request):
    if request is None:
        return None
    forwardee = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwardee:
        return forwardee.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def journaliser(request, action, objet=None, details=""):
    """Enregistre une opération dans le journal d'audit."""
    utilisateur = getattr(request, "user", None)
    if utilisateur is not None and not utilisateur.is_authenticated:
        utilisateur = None
    JournalAudit.objects.create(
        utilisateur=utilisateur,
        action=action,
        modele=objet.__class__.__name__ if objet is not None else "",
        objet_id=str(getattr(objet, "pk", "") or ""),
        details=details,
        adresse_ip=adresse_ip(request),
    )
