from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import journaliser
from medicaments.models import Medicament
from stock.models import LotStock
from stock.services import StockError
from utilisateurs.decorators import CAISSIER, PHARMACIEN, RESPONSABLE, role_required

from .forms import CheckoutForm, RetourForm
from .models import LigneVente, Paiement, Vente
from .services import enregistrer_retour, lots_fefo, valider_vente

CLE_PANIER = "panier_vente"


def _panier(request):
    return request.session.get(CLE_PANIER, {})


def _enregistrer_panier(request, panier):
    request.session[CLE_PANIER] = panier
    request.session.modified = True


@role_required(PHARMACIEN, CAISSIER)
def caisse(request):
    recherche = request.GET.get("q", "").strip()
    medicaments = []
    if recherche:
        medicaments = (
            Medicament.objects.filter(statut=Medicament.Statut.ACTIF)
            .filter(Q(nom__icontains=recherche) | Q(code_barres__icontains=recherche))
            .select_related("categorie")
            .order_by("nom")[:30]
        )
        for medicament in medicaments:
            medicament.lots_vente = list(lots_fefo(medicament)[:8])
    panier = _panier(request)
    return render(
        request,
        "ventes/caisse.html",
        {
            "recherche": recherche,
            "medicaments": medicaments,
            "nombre_panier": sum(panier.values()),
        },
    )


@role_required(PHARMACIEN, CAISSIER)
@require_POST
def ajouter_au_panier(request):
    try:
        lot = LotStock.objects.select_related("medicament").get(
            pk=request.POST.get("lot_id")
        )
    except (LotStock.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Lot introuvable.")
        return redirect("caisse")
    try:
        quantite = int(request.POST.get("quantite", "1"))
    except ValueError:
        quantite = 0
    if quantite <= 0:
        messages.error(request, "La quantité doit être supérieure à zéro.")
        return redirect("caisse")
    if not lot.est_delivrable:
        messages.error(request, "Ce lot n'est pas disponible à la vente.")
        return redirect("caisse")
    if lot.medicament.statut != Medicament.Statut.ACTIF:
        messages.error(request, "Ce médicament n'est pas disponible à la vente.")
        return redirect("caisse")

    panier = _panier(request)
    cle = str(lot.pk)
    nouvelle = panier.get(cle, 0) + quantite
    if nouvelle > lot.quantite:
        messages.error(
            request,
            f"Stock insuffisant pour le lot {lot.numero_lot} "
            f"({lot.quantite} disponible(s)).",
        )
        return redirect("caisse")
    panier[cle] = nouvelle
    _enregistrer_panier(request, panier)
    messages.success(request, f"{lot.medicament.nom} ajouté au panier.")
    return redirect("caisse")


@role_required(PHARMACIEN, CAISSIER)
def panier(request):
    elements = []
    total = 0
    panier = _panier(request)
    for lot_id, quantite in list(panier.items()):
        try:
            lot = LotStock.objects.select_related("medicament").get(pk=lot_id)
        except LotStock.DoesNotExist:
            panier.pop(lot_id, None)
            _enregistrer_panier(request, panier)
            continue
        prix = lot.medicament.prix_vente
        sous_total = prix * quantite
        total += sous_total
        elements.append(
            {
                "lot": lot,
                "quantite": quantite,
                "prix": prix,
                "sous_total": sous_total,
                "probleme": (not lot.est_delivrable) or lot.quantite < quantite,
            }
        )
    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            lignes = [
                {"lot_id": int(lot_id), "quantite": quantite}
                for lot_id, quantite in panier.items()
            ]
            try:
                vente = valider_vente(
                    utilisateur=request.user,
                    mode_paiement=form.cleaned_data["mode_paiement"],
                    lignes=lignes,
                    client=form.cleaned_data["client"],
                    reference_paiement=form.cleaned_data["reference_paiement"],
                )
            except StockError as exc:
                messages.error(request, str(exc))
            else:
                request.session[CLE_PANIER] = {}
                journaliser(
                    request,
                    "Vente validée",
                    vente,
                    f"{vente.numero} : {vente.total}",
                )
                messages.success(request, f"Vente {vente.numero} validée.")
                return redirect("detail_vente", pk=vente.pk)
    else:
        form = CheckoutForm()
    return render(
        request,
        "ventes/panier.html",
        {"elements": elements, "total": total, "form": form},
    )


@role_required(PHARMACIEN, CAISSIER)
@require_POST
def retirer_du_panier(request, lot_id):
    panier = _panier(request)
    panier.pop(str(lot_id), None)
    _enregistrer_panier(request, panier)
    messages.info(request, "Ligne retirée du panier.")
    return redirect("panier")


@role_required(PHARMACIEN, CAISSIER)
@require_POST
def vider_panier(request):
    request.session[CLE_PANIER] = {}
    messages.info(request, "Panier vidé.")
    return redirect("caisse")


@role_required(PHARMACIEN, CAISSIER, RESPONSABLE)
def liste_ventes(request):
    ventes = Vente.objects.select_related("client", "utilisateur")
    recherche = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    if recherche:
        ventes = ventes.filter(
            Q(numero__icontains=recherche)
            | Q(client__nom__icontains=recherche)
        )
    if statut:
        ventes = ventes.filter(statut=statut)
    paginator = Paginator(ventes, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "ventes/liste.html",
        {
            "page": page,
            "ventes": page.object_list,
            "recherche": recherche,
            "statut_selectionne": statut,
            "statuts": Vente.Statut.choices,
        },
    )


@role_required(PHARMACIEN, CAISSIER, RESPONSABLE)
def detail_vente(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "utilisateur"), pk=pk
    )
    return render(
        request,
        "ventes/detail.html",
        {
            "vente": vente,
            "lignes": vente.lignes.select_related("medicament", "lot"),
            "paiements": vente.paiements.all(),
            "retours": vente.retours.select_related("ligne_vente", "utilisateur"),
        },
    )


@role_required(PHARMACIEN, CAISSIER)
def retour_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if not vente.est_retournable:
        messages.error(request, "Cette vente ne peut pas faire l'objet d'un retour.")
        return redirect("detail_vente", pk=vente.pk)
    if request.method == "POST":
        form = RetourForm(request.POST, vente=vente)
        if form.is_valid():
            ligne = form.cleaned_data["ligne_vente"]
            try:
                retour = enregistrer_retour(
                    vente=vente,
                    ligne_vente=ligne,
                    quantite=form.cleaned_data["quantite"],
                    motif=form.cleaned_data["motif"],
                    utilisateur=request.user,
                    remise_en_stock=form.cleaned_data["remise_en_stock"],
                )
            except StockError as exc:
                messages.error(request, str(exc))
            else:
                journaliser(
                    request,
                    "Retour de vente",
                    retour,
                    f"{vente.numero} : {retour.quantite} x {ligne.medicament.nom}",
                )
                messages.success(
                    request,
                    f"Retour enregistré. Montant remboursé : {retour.montant_rembourse}.",
                )
                return redirect("detail_vente", pk=vente.pk)
    else:
        form = RetourForm(vente=vente)
    return render(
        request,
        "ventes/retour.html",
        {
            "vente": vente,
            "form": form,
            "lignes": vente.lignes.select_related("medicament"),
        },
    )


@role_required(PHARMACIEN, CAISSIER)
@require_POST
def confirmer_paiement(request, pk):
    paiement = get_object_or_404(
        Paiement.objects.select_related("vente"), pk=pk
    )
    if paiement.statut != Paiement.Statut.EN_ATTENTE:
        messages.info(request, "Ce paiement n'est pas en attente de confirmation.")
    else:
        paiement.statut = Paiement.Statut.CONFIRME
        if not paiement.reference:
            paiement.reference = request.POST.get("reference", "").strip()
        paiement.save(update_fields=["statut", "reference"])
        journaliser(
            request,
            "Confirmation de paiement",
            paiement,
            f"{paiement.vente.numero} : {paiement.montant}",
        )
        messages.success(request, "Paiement confirmé.")
    return redirect("detail_vente", pk=paiement.vente.pk)
