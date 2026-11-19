"""Services métier des ventes (validation atomique et FEFO)."""
from django.db import transaction

from stock.models import LotStock
from stock.services import StockError, sortir_stock

from .models import LigneVente, Paiement, Vente


def lots_fefo(medicament):
    """Retourne les lots délivrables du plus proche de la péremption au plus tardif."""
    return medicament.lots_delivrables


def valider_vente(
    *,
    utilisateur,
    mode_paiement,
    lignes,
    client=None,
    reference_paiement="",
):
    """Crée une vente et réalise les sorties de stock dans une transaction unique.

    `lignes` est une liste de dictionnaires : {"lot_id": int, "quantite": int}.
    """
    if not lignes:
        raise StockError("Le panier est vide.")
    if mode_paiement not in Vente.ModePaiement.values:
        raise StockError("Mode de paiement invalide.")

    with transaction.atomic():
        vente = Vente.objects.create(
            client=client,
            utilisateur=utilisateur,
            mode_paiement=mode_paiement,
        )

        for element in lignes:
            try:
                lot = (
                    LotStock.objects.select_for_update()
                    .select_related("medicament")
                    .get(pk=element["lot_id"])
                )
            except LotStock.DoesNotExist:
                raise StockError("Un lot du panier n'existe plus.")
            try:
                quantite = int(element["quantite"])
            except (TypeError, ValueError):
                raise StockError("Quantité invalide dans le panier.")

            if quantite <= 0:
                raise StockError("La quantité doit être supérieure à zéro.")
            if lot.medicament.statut != "ACTIF":
                raise StockError(
                    f"Le médicament {lot.medicament.nom} n'est pas disponible à la vente."
                )
            if not lot.est_delivrable:
                raise StockError(
                    f"Le lot {lot.numero_lot} de {lot.medicament.nom} "
                    "est périmé, bloqué ou épuisé."
                )
            if lot.quantite < quantite:
                raise StockError(
                    f"Stock insuffisant pour {lot.medicament.nom} "
                    f"({lot.quantite} disponible(s))."
                )

            prix = lot.medicament.prix_vente
            LigneVente.objects.create(
                vente=vente,
                medicament=lot.medicament,
                lot=lot,
                quantite=quantite,
                prix_unitaire=prix,
            )
            sortir_stock(
                lot,
                quantite,
                utilisateur=utilisateur,
                motif="Vente",
                reference=vente.numero,
            )

        statut_paiement = Paiement.Statut.CONFIRME
        if (
            mode_paiement
            in (Vente.ModePaiement.MOBILE_MONEY, Vente.ModePaiement.CARTE)
            and not reference_paiement
        ):
            statut_paiement = Paiement.Statut.EN_ATTENTE
        Paiement.objects.create(
            vente=vente,
            montant=vente.total,
            mode=mode_paiement,
            statut=statut_paiement,
            reference=reference_paiement,
        )
        return vente


@transaction.atomic
def enregistrer_retour(*, vente, ligne_vente, quantite, motif, utilisateur, remise_en_stock=True):
    """Enregistre un retour traçable et réintègre le stock si autorisé."""
    from datetime import date

    from stock.services import retourner_stock

    from .models import RetourVente

    quantite = int(quantite)
    if quantite <= 0:
        raise StockError("La quantité retournée doit être supérieure à zéro.")
    if quantite > ligne_vente.quantite_retournable:
        raise StockError(
            f"La quantité retournée dépasse la quantité encore retournable "
            f"({ligne_vente.quantite_retournable})."
        )

    montant = quantite * ligne_vente.prix_unitaire
    retour = RetourVente.objects.create(
        vente=vente,
        ligne_vente=ligne_vente,
        quantite=quantite,
        motif=motif,
        utilisateur=utilisateur,
        remise_en_stock=remise_en_stock,
        montant_rembourse=montant,
    )

    lot = ligne_vente.lot
    if remise_en_stock and lot is not None:
        if lot.date_peremption < date.today():
            retour.remise_en_stock = False
            retour.save(update_fields=["remise_en_stock"])
        else:
            retourner_stock(
                lot,
                quantite,
                utilisateur=utilisateur,
                motif=f"Retour vente {vente.numero}",
                reference=vente.numero,
            )
    return retour
