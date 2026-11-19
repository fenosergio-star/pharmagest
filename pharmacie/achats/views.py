from datetime import datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import journaliser
from stock.services import StockError, entrer_stock
from utilisateurs.decorators import GESTIONNAIRE, PHARMACIEN, role_required

from .forms import CommandeAchatForm, LigneAchatFormSet, ReceptionForm
from .models import CommandeAchat, LigneReception, ReceptionAchat

ROLES = (PHARMACIEN, GESTIONNAIRE)


@role_required(*ROLES)
def liste_commandes(request):
    commandes = CommandeAchat.objects.select_related("fournisseur", "utilisateur")
    statut = request.GET.get("statut", "")
    recherche = request.GET.get("q", "").strip()
    if statut:
        commandes = commandes.filter(statut=statut)
    if recherche:
        commandes = commandes.filter(
            Q(numero__icontains=recherche)
            | Q(fournisseur__nom__icontains=recherche)
        )
    paginator = Paginator(commandes, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "achats/liste.html",
        {
            "page": page,
            "commandes": page.object_list,
            "statut_selectionne": statut,
            "recherche": recherche,
            "statuts": CommandeAchat.Statut.choices,
        },
    )


@role_required(*ROLES)
def detail_commande(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related("fournisseur", "utilisateur"), pk=pk
    )
    return render(
        request,
        "achats/detail.html",
        {
            "commande": commande,
            "lignes": commande.lignes.select_related("medicament"),
            "receptions": commande.receptions.select_related("utilisateur"),
        },
    )


@role_required(*ROLES)
def creer_commande(request):
    commande = CommandeAchat()
    if request.method == "POST":
        form = CommandeAchatForm(request.POST)
        formset = LigneAchatFormSet(request.POST, instance=commande)
        if form.is_valid() and formset.is_valid():
            commande = form.save(commit=False)
            commande.utilisateur = request.user
            commande.save()
            formset.instance = commande
            formset.save()
            journaliser(request, "Création d'une commande", commande, commande.numero)
            messages.success(request, f"Commande {commande.numero} créée en brouillon.")
            return redirect("detail_commande", pk=commande.pk)
    else:
        form = CommandeAchatForm()
        formset = LigneAchatFormSet(instance=commande)
    return render(
        request,
        "achats/form.html",
        {"form": form, "formset": formset, "commande": commande, "titre": "Nouvelle commande d'achat"},
    )


@role_required(*ROLES)
def modifier_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if not commande.est_modifiable:
        messages.error(request, "Seules les commandes en brouillon peuvent être modifiées.")
        return redirect("detail_commande", pk=commande.pk)
    if request.method == "POST":
        form = CommandeAchatForm(request.POST, instance=commande)
        formset = LigneAchatFormSet(request.POST, instance=commande)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            journaliser(request, "Modification d'une commande", commande, commande.numero)
            messages.success(request, "Commande mise à jour.")
            return redirect("detail_commande", pk=commande.pk)
    else:
        form = CommandeAchatForm(instance=commande)
        formset = LigneAchatFormSet(instance=commande)
    return render(
        request,
        "achats/form.html",
        {"form": form, "formset": formset, "commande": commande, "titre": "Modifier la commande"},
    )


@role_required(*ROLES)
@require_POST
def valider_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut != CommandeAchat.Statut.BROUILLON:
        messages.error(request, "Cette commande ne peut plus être validée.")
    elif not commande.lignes.exists():
        messages.error(request, "Une commande vide ne peut pas être validée.")
    else:
        commande.statut = CommandeAchat.Statut.COMMANDEE
        commande.save(update_fields=["statut"])
        journaliser(request, "Validation d'une commande", commande, commande.numero)
        messages.success(request, "Commande validée. Le stock n'est pas encore modifié.")
    return redirect("detail_commande", pk=commande.pk)


@role_required(*ROLES)
@require_POST
def annuler_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.receptions.exists() or commande.statut == CommandeAchat.Statut.RECEPTIONNEE:
        messages.error(
            request,
            "Une commande déjà réceptionnée ne peut pas être annulée. "
            "Utilisez une correction d'inventaire traçable.",
        )
    elif commande.statut == CommandeAchat.Statut.ANNULEE:
        messages.info(request, "Cette commande est déjà annulée.")
    else:
        commande.statut = CommandeAchat.Statut.ANNULEE
        commande.save(update_fields=["statut"])
        journaliser(request, "Annulation d'une commande", commande, commande.numero)
        messages.success(request, "Commande annulée.")
    return redirect("detail_commande", pk=commande.pk)


@role_required(*ROLES)
def receptionner_commande(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related("fournisseur"), pk=pk
    )
    if not commande.peut_etre_receptionnee:
        messages.error(
            request,
            "La commande doit être validée avant de pouvoir être réceptionnée.",
        )
        return redirect("detail_commande", pk=commande.pk)

    lignes = list(
        commande.lignes.select_related("medicament").filter(quantite_recue__lt=F("quantite"))
    )

    if request.method == "POST":
        form = ReceptionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    reception = ReceptionAchat.objects.create(
                        commande=commande,
                        utilisateur=request.user,
                        notes=form.cleaned_data["notes"],
                    )
                    total_recu = 0
                    for ligne in lignes:
                        cle = str(ligne.pk)
                        quantite_brute = request.POST.get(f"qte_{cle}", "0").strip() or "0"
                        try:
                            quantite = int(quantite_brute)
                        except ValueError:
                            raise StockError(
                                f"Quantité invalide pour {ligne.medicament.nom}."
                            )
                        if quantite <= 0:
                            continue
                        if quantite > ligne.reste:
                            raise StockError(
                                f"La quantité reçue pour {ligne.medicament.nom} "
                                f"dépasse le reste ({ligne.reste})."
                            )
                        numero_lot = request.POST.get(f"lot_{cle}", "").strip()
                        date_brute = request.POST.get(f"peremption_{cle}", "").strip()
                        if not numero_lot:
                            raise StockError(
                                f"Le numéro de lot est obligatoire pour {ligne.medicament.nom}."
                            )
                        try:
                            date_peremption = datetime.strptime(
                                date_brute, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            raise StockError(
                                f"Date de péremption invalide pour {ligne.medicament.nom}."
                            )
                        lot = entrer_stock(
                            ligne.medicament,
                            numero_lot,
                            date_peremption,
                            quantite,
                            utilisateur=request.user,
                            motif=f"Réception {reception.numero}",
                            reference=commande.numero,
                        )
                        LigneReception.objects.create(
                            reception=reception,
                            ligne_achat=ligne,
                            lot=lot,
                            numero_lot=numero_lot,
                            date_peremption=date_peremption,
                            quantite=quantite,
                        )
                        ligne.quantite_recue += quantite
                        ligne.save(update_fields=["quantite_recue"])
                        total_recu += quantite

                    if total_recu == 0:
                        raise StockError("Aucune quantité n'a été saisie.")

                    if commande.reste_a_recevoir == 0:
                        commande.statut = CommandeAchat.Statut.RECEPTIONNEE
                    else:
                        commande.statut = CommandeAchat.Statut.PARTIELLE
                    commande.save(update_fields=["statut"])
                    journaliser(
                        request,
                        "Réception d'achat",
                        reception,
                        f"{commande.numero} : {total_recu} unité(s)",
                    )
                messages.success(
                    request,
                    f"Réception {reception.numero} enregistrée : {total_recu} unité(s).",
                )
                return redirect("detail_commande", pk=commande.pk)
            except StockError as exc:
                messages.error(request, str(exc))
    else:
        form = ReceptionForm()

    return render(
        request,
        "achats/reception.html",
        {"commande": commande, "lignes": lignes, "form": form},
    )
