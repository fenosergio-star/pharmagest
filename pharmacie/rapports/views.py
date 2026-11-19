from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from achats.models import CommandeAchat, LigneAchat, ReceptionAchat
from medicaments.models import Medicament
from stock.models import LotStock
from stock.services import lots_peremption_proche
from utilisateurs.decorators import (
    CAISSIER,
    GESTIONNAIRE,
    PHARMACIEN,
    RESPONSABLE,
    role_required,
)
from ventes.models import LigneVente, Paiement, RetourVente, Vente

from . import pdf

TOUS = (PHARMACIEN, GESTIONNAIRE, CAISSIER, RESPONSABLE)

def _periode(request):
    aujourdhui = timezone.localdate()
    debut_brut = request.GET.get("date_debut", "")
    fin_brut = request.GET.get("date_fin", "")
    try:
        debut = datetime.strptime(debut_brut, "%Y-%m-%d").date()
    except ValueError:
        debut = aujourdhui - timedelta(days=30)
    try:
        fin = datetime.strptime(fin_brut, "%Y-%m-%d").date()
    except ValueError:
        fin = aujourdhui
    if debut > fin:
        debut, fin = fin, debut
    return debut, fin


def _statistiques_periode(debut, fin):
    ventes = Vente.objects.filter(
        statut=Vente.Statut.VALIDEE, date_vente__date__range=(debut, fin)
    )
    lignes = list(
        LigneVente.objects.filter(vente__in=ventes).select_related("medicament")
    )
    chiffre_affaires = sum(
        (ligne.quantite * ligne.prix_unitaire for ligne in lignes), Decimal("0")
    )
    marge = sum(
        (
            ligne.quantite * (ligne.prix_unitaire - ligne.medicament.prix_achat)
            for ligne in lignes
        ),
        Decimal("0"),
    )
    remboursements = (
        RetourVente.objects.filter(vente__in=ventes).aggregate(
            total=Sum("montant_rembourse")
        )["total"]
        or Decimal("0")
    )
    encaissements = (
        Paiement.objects.filter(vente__in=ventes, statut=Paiement.Statut.CONFIRME)
        .aggregate(total=Sum("montant"))["total"]
        or Decimal("0")
    )
    commandes = CommandeAchat.objects.filter(
        date_commande__date__range=(debut, fin)
    ).exclude(statut=CommandeAchat.Statut.ANNULEE)
    lignes_achat = LigneAchat.objects.filter(commande__in=commandes)
    achats = sum(
        (ligne.quantite * ligne.prix_achat for ligne in lignes_achat), Decimal("0")
    )
    produits = {}
    for ligne in lignes:
        entree = produits.setdefault(
            ligne.medicament.nom, {"medicament__nom": ligne.medicament.nom, "quantite": 0, "montant": Decimal("0")}
        )
        entree["quantite"] += ligne.quantite
        entree["montant"] += ligne.quantite * ligne.prix_unitaire
    top_produits = sorted(produits.values(), key=lambda p: p["quantite"], reverse=True)[:10]
    return {
        "debut": debut,
        "fin": fin,
        "nombre_ventes": ventes.count(),
        "chiffre_affaires": chiffre_affaires,
        "encaissements": encaissements,
        "remboursements": remboursements,
        "marge_commerciale": marge,
        "achats": achats,
        "nombre_commandes": commandes.count(),
        "top_produits": top_produits,
        "ventes": ventes,
    }


@role_required(*TOUS)
def dashboard(request):
    aujourdhui = timezone.localdate()
    ventes_jour = Vente.objects.filter(
        statut=Vente.Statut.VALIDEE, date_vente__date=aujourdhui
    )
    montant_jour = sum(
        (
            ligne.quantite * ligne.prix_unitaire
            for ligne in LigneVente.objects.filter(vente__in=ventes_jour)
        ),
        Decimal("0"),
    )
    medicaments_actifs = Medicament.objects.filter(statut=Medicament.Statut.ACTIF)
    stocks_faibles = [
        medicament
        for medicament in medicaments_actifs.select_related("categorie")
        if medicament.stock_disponible <= medicament.seuil_alerte
    ]
    stocks_faibles.sort(key=lambda m: m.stock_disponible)
    peremptions = lots_peremption_proche().select_related("medicament")
    debut, fin = _periode(request)
    statistiques = _statistiques_periode(debut, fin)
    return render(
        request,
        "rapports/dashboard.html",
        {
            "medicaments_actifs": medicaments_actifs.count(),
            "ventes_jour": ventes_jour.count(),
            "montant_jour": montant_jour,
            "stocks_faibles": stocks_faibles[:8],
            "nombre_stocks_faibles": len(stocks_faibles),
            "peremptions": peremptions[:8],
            "nombre_peremptions": peremptions.count(),
            "ventes_recentes": Vente.objects.select_related("client", "utilisateur")[:8],
            "statistiques": statistiques,
        },
    )


@role_required(*TOUS)
def statistiques(request):
    debut, fin = _periode(request)
    contexte = _statistiques_periode(debut, fin)
    contexte["jours_alerte"] = 30
    return render(request, "rapports/statistiques.html", contexte)


def _reponse_pdf(contenu, nom):
    reponse = HttpResponse(contenu, content_type="application/pdf")
    reponse["Content-Disposition"] = f'inline; filename="{nom}"'
    return reponse


@role_required(*TOUS)
def pdf_recu(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    return _reponse_pdf(pdf.recu_vente(vente), f"recu-{vente.numero}.pdf")


@role_required(*TOUS)
def pdf_facture(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    return _reponse_pdf(pdf.facture_vente(vente), f"facture-{vente.numero}.pdf")


@role_required(PHARMACIEN, GESTIONNAIRE, RESPONSABLE)
def pdf_bon_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    return _reponse_pdf(pdf.bon_commande(commande), f"commande-{commande.numero}.pdf")


@role_required(PHARMACIEN, GESTIONNAIRE, RESPONSABLE)
def pdf_bon_reception(request, pk):
    reception = get_object_or_404(ReceptionAchat, pk=pk)
    return _reponse_pdf(pdf.bon_reception(reception), f"reception-{reception.numero}.pdf")


@role_required(PHARMACIEN, GESTIONNAIRE, RESPONSABLE)
def pdf_rapport_stock(request):
    lots = LotStock.objects.select_related("medicament").order_by(
        "medicament__nom", "date_peremption"
    )
    return _reponse_pdf(pdf.rapport_stock(lots), "rapport-stock.pdf")


@role_required(PHARMACIEN, GESTIONNAIRE, RESPONSABLE)
def pdf_rapport_ventes(request):
    debut, fin = _periode(request)
    ventes = (
        Vente.objects.filter(
            statut=Vente.Statut.VALIDEE, date_vente__date__range=(debut, fin)
        )
        .select_related("client", "utilisateur")
        .order_by("date_vente")
    )
    return _reponse_pdf(
        pdf.rapport_ventes(ventes, debut, fin), "rapport-ventes.pdf"
    )


@role_required(PHARMACIEN, GESTIONNAIRE, RESPONSABLE)
def pdf_rapport_achats(request):
    debut, fin = _periode(request)
    commandes = (
        CommandeAchat.objects.filter(date_commande__date__range=(debut, fin))
        .exclude(statut=CommandeAchat.Statut.ANNULEE)
        .select_related("fournisseur")
        .order_by("date_commande")
    )
    return _reponse_pdf(
        pdf.rapport_achats(commandes, debut, fin), "rapport-achats.pdf"
    )


@role_required(*TOUS)
def pdf_peremptions(request):
    lots = lots_peremption_proche().select_related("medicament")
    return _reponse_pdf(
        pdf.rapport_peremptions(lots, 30), "produits-peremption.pdf"
    )
