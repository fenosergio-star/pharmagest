from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import journaliser
from medicaments.models import Medicament
from utilisateurs.decorators import (
    CAISSIER,
    GESTIONNAIRE,
    PHARMACIEN,
    RESPONSABLE,
    role_required,
)

from .forms import CorrectionStockForm
from .models import LotStock, MouvementStock
from .services import StockError, corriger_stock, lots_peremption_proche

ROLES_LECTURE = (PHARMACIEN, GESTIONNAIRE, CAISSIER, RESPONSABLE)
ROLES_GESTION = (PHARMACIEN, GESTIONNAIRE)


@role_required(*ROLES_LECTURE)
def liste_stock(request):
    recherche = request.GET.get("q", "").strip()
    filtre = request.GET.get("etat", "")
    medicaments = Medicament.objects.filter(statut=Medicament.Statut.ACTIF).annotate(
        qte_totale=Sum("lots__quantite")
    )
    if recherche:
        medicaments = medicaments.filter(
            Q(nom__icontains=recherche) | Q(code_barres__icontains=recherche)
        )
    medicaments = medicaments.order_by("nom")

    aujourdhui = timezone.localdate()
    lignes = []
    for medicament in medicaments:
        disponible = medicament.stock_disponible
        if filtre == "rupture" and disponible != 0:
            continue
        if filtre == "faible" and not (0 < disponible <= medicament.seuil_alerte):
            continue
        lignes.append(
            {
                "medicament": medicament,
                "disponible": disponible,
                "total": medicament.stock_total,
                "faible": disponible <= medicament.seuil_alerte,
                "rupture": disponible == 0,
                "peremption_proche": medicament.lots.filter(
                    quantite__gt=0,
                    date_peremption__gte=aujourdhui,
                    date_peremption__lte=aujourdhui + timedelta(days=30),
                ).exists(),
            }
        )
    paginator = Paginator(lignes, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "stock/liste.html",
        {
            "page": page,
            "lignes": page.object_list,
            "recherche": recherche,
            "filtre": filtre,
        },
    )


@role_required(*ROLES_LECTURE)
def liste_lots(request):
    lots = LotStock.objects.select_related("medicament")
    recherche = request.GET.get("q", "").strip()
    etat = request.GET.get("etat", "")
    if recherche:
        lots = lots.filter(
            Q(medicament__nom__icontains=recherche) | Q(numero_lot__icontains=recherche)
        )
    if etat == "perimes":
        lots = lots.filter(date_peremption__lt=timezone.localdate())
    elif etat == "proches":
        lots = lots.filter(
            date_peremption__gte=timezone.localdate(),
            date_peremption__lte=timezone.localdate()
            + timezone.timedelta(days=30),
        )
    elif etat == "bloques":
        lots = lots.filter(bloque=True)
    elif etat == "disponibles":
        lots = lots.filter(quantite__gt=0, bloque=False)
    paginator = Paginator(lots.order_by("date_peremption"), 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "stock/lots.html",
        {"page": page, "lots": page.object_list, "recherche": recherche, "etat": etat},
    )


@role_required(*ROLES_LECTURE)
def liste_mouvements(request):
    mouvements = MouvementStock.objects.select_related(
        "medicament", "lot", "utilisateur"
    )
    type_mouvement = request.GET.get("type", "")
    recherche = request.GET.get("q", "").strip()
    if type_mouvement:
        mouvements = mouvements.filter(type=type_mouvement)
    if recherche:
        mouvements = mouvements.filter(medicament__nom__icontains=recherche)
    paginator = Paginator(mouvements, 30)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "stock/mouvements.html",
        {
            "page": page,
            "mouvements": page.object_list,
            "type_selectionne": type_mouvement,
            "recherche": recherche,
            "types": MouvementStock.Type.choices,
        },
    )


@role_required(*ROLES_LECTURE)
def liste_peremptions(request):
    lots = lots_peremption_proche().select_related("medicament")
    return render(
        request,
        "stock/peremptions.html",
        {"lots": lots, "aujourdhui": timezone.localdate()},
    )


@role_required(*ROLES_GESTION)
@require_POST
def corriger_lot(request, pk):
    lot = get_object_or_404(LotStock.objects.select_related("medicament"), pk=pk)
    form = CorrectionStockForm(request.POST)
    if form.is_valid():
        try:
            corriger_stock(
                lot,
                form.cleaned_data["nouvelle_quantite"],
                utilisateur=request.user,
                motif=form.cleaned_data["motif"],
            )
            journaliser(
                request,
                "Correction de stock",
                lot,
                f"{lot.medicament.nom} / lot {lot.numero_lot} : nouvelle quantité "
                f"{form.cleaned_data['nouvelle_quantite']}",
            )
            messages.success(request, "Correction d'inventaire enregistrée.")
        except StockError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "La quantité corrigée est invalide.")
    return redirect(request.POST.get("suivant") or "liste_lots")


@role_required(*ROLES_GESTION)
@require_POST
def basculer_lot(request, pk):
    lot = get_object_or_404(LotStock, pk=pk)
    lot.bloque = not lot.bloque
    lot.save(update_fields=["bloque"])
    etat = "bloqué" if lot.bloque else "débloqué"
    journaliser(request, f"Lot {etat}", lot, f"{lot.medicament.nom} / {lot.numero_lot}")
    messages.success(request, f"Le lot a été {etat}.")
    return redirect(request.POST.get("suivant") or "liste_lots")
