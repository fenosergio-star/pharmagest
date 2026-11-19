"""Services métier de gestion du stock.

Toutes les opérations qui modifient une quantité de lot créent un mouvement
traçable et verrouillent la ligne concernée grâce à select_for_update().
Elles doivent être appelées à l'intérieur d'une transaction atomique.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import LotStock, MouvementStock


class StockError(Exception):
    """Erreur métier liée au stock."""


@transaction.atomic
def entrer_stock(
    medicament,
    numero_lot,
    date_peremption,
    quantite,
    utilisateur=None,
    motif="Réception",
    reference="",
):
    """Crée ou alimente un lot et enregistre le mouvement d'entrée."""
    numero_lot = (numero_lot or "").strip()
    if not numero_lot:
        raise StockError("Le numéro de lot est obligatoire.")
    try:
        quantite = int(quantite)
    except (TypeError, ValueError):
        raise StockError("La quantité doit être un nombre entier.")
    if quantite <= 0:
        raise StockError("La quantité à réceptionner doit être supérieure à zéro.")
    if date_peremption is None:
        raise StockError("La date de péremption est obligatoire.")

    lot = (
        LotStock.objects.select_for_update()
        .filter(medicament=medicament, numero_lot=numero_lot)
        .first()
    )
    if lot is None:
        lot = LotStock.objects.create(
            medicament=medicament,
            numero_lot=numero_lot,
            date_peremption=date_peremption,
            quantite=quantite,
        )
    else:
        if lot.date_peremption != date_peremption:
            lot.date_peremption = date_peremption
        lot.quantite += quantite
        lot.save(update_fields=["quantite", "date_peremption"])

    MouvementStock.objects.create(
        medicament=medicament,
        lot=lot,
        type=MouvementStock.Type.ENTREE,
        quantite=quantite,
        motif=motif,
        reference=reference,
        utilisateur=utilisateur,
    )
    return lot


@transaction.atomic
def sortir_stock(lot, quantite, utilisateur=None, motif="Vente", reference=""):
    """Décrémente un lot après vérification des règles de délivrance."""
    lot = LotStock.objects.select_for_update().select_related("medicament").get(pk=lot.pk)
    try:
        quantite = int(quantite)
    except (TypeError, ValueError):
        raise StockError("La quantité doit être un nombre entier.")
    if quantite <= 0:
        raise StockError("La quantité doit être supérieure à zéro.")
    if lot.est_perime:
        raise StockError(f"Le lot {lot.numero_lot} est périmé et ne peut pas être vendu.")
    if lot.bloque:
        raise StockError(f"Le lot {lot.numero_lot} est bloqué et ne peut pas être vendu.")
    if lot.quantite < quantite:
        raise StockError(
            f"Stock insuffisant pour le lot {lot.numero_lot} "
            f"({lot.quantite} disponible(s), {quantite} demandé(s))."
        )

    lot.quantite -= quantite
    lot.save(update_fields=["quantite"])
    MouvementStock.objects.create(
        medicament=lot.medicament,
        lot=lot,
        type=MouvementStock.Type.SORTIE,
        quantite=-quantite,
        motif=motif,
        reference=reference,
        utilisateur=utilisateur,
    )
    return lot


@transaction.atomic
def retourner_stock(lot, quantite, utilisateur=None, motif="Retour client", reference=""):
    """Réintègre un lot après un retour autorisé."""
    lot = LotStock.objects.select_for_update().select_related("medicament").get(pk=lot.pk)
    quantite = int(quantite)
    if quantite <= 0:
        raise StockError("La quantité retournée doit être supérieure à zéro.")
    lot.quantite += quantite
    lot.save(update_fields=["quantite"])
    MouvementStock.objects.create(
        medicament=lot.medicament,
        lot=lot,
        type=MouvementStock.Type.RETOUR,
        quantite=quantite,
        motif=motif,
        reference=reference,
        utilisateur=utilisateur,
    )
    return lot


@transaction.atomic
def corriger_stock(lot, nouvelle_quantite, utilisateur=None, motif="Inventaire physique"):
    """Applique une correction d'inventaire traçable."""
    lot = LotStock.objects.select_for_update().select_related("medicament").get(pk=lot.pk)
    nouvelle_quantite = int(nouvelle_quantite)
    if nouvelle_quantite < 0:
        raise StockError("La quantité corrigée ne peut pas être négative.")
    delta = nouvelle_quantite - lot.quantite
    if delta == 0:
        return lot
    lot.quantite = nouvelle_quantite
    lot.save(update_fields=["quantite"])
    MouvementStock.objects.create(
        medicament=lot.medicament,
        lot=lot,
        type=MouvementStock.Type.CORRECTION,
        quantite=delta,
        motif=motif,
        utilisateur=utilisateur,
    )
    return lot


def lots_peremption_proche(jours=None):
    from django.conf import settings

    jours = settings.JOURS_ALERTE_PEREMPTION if jours is None else jours
    limite = timezone.localdate() + timedelta(days=jours)
    return LotStock.objects.filter(
        quantite__gt=0,
        bloque=False,
        date_peremption__lte=limite,
    ).select_related("medicament").order_by("date_peremption")
