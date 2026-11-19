from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import journaliser
from utilisateurs.decorators import GESTIONNAIRE, PHARMACIEN, role_required

from .forms import FournisseurForm
from .models import Fournisseur


@role_required(PHARMACIEN, GESTIONNAIRE)
def liste_fournisseurs(request):
    fournisseurs = Fournisseur.objects.all()
    recherche = request.GET.get("q", "").strip()
    if recherche:
        fournisseurs = fournisseurs.filter(
            Q(nom__icontains=recherche) | Q(telephone__icontains=recherche)
        )
    return render(
        request,
        "fournisseurs/liste.html",
        {"fournisseurs": fournisseurs, "recherche": recherche},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def detail_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    commandes = fournisseur.commandes.select_related("utilisateur").order_by("-date_commande")
    return render(
        request,
        "fournisseurs/detail.html",
        {"fournisseur": fournisseur, "commandes": commandes},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def creer_fournisseur(request):
    if request.method == "POST":
        form = FournisseurForm(request.POST)
        if form.is_valid():
            fournisseur = form.save()
            journaliser(request, "Création d'un fournisseur", fournisseur, fournisseur.nom)
            messages.success(request, "Fournisseur créé.")
            return redirect("detail_fournisseur", pk=fournisseur.pk)
    else:
        form = FournisseurForm()
    return render(
        request,
        "fournisseurs/form.html",
        {"form": form, "titre": "Ajouter un fournisseur"},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def modifier_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == "POST":
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            journaliser(request, "Modification d'un fournisseur", fournisseur, fournisseur.nom)
            messages.success(request, "Fournisseur mis à jour.")
            return redirect("detail_fournisseur", pk=fournisseur.pk)
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(
        request,
        "fournisseurs/form.html",
        {"form": form, "fournisseur": fournisseur, "titre": "Modifier un fournisseur"},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
@require_POST
def basculer_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    fournisseur.actif = not fournisseur.actif
    fournisseur.save(update_fields=["actif"])
    etat = "activé" if fournisseur.actif else "désactivé"
    journaliser(request, f"Fournisseur {etat}", fournisseur, fournisseur.nom)
    messages.success(request, f"Fournisseur {etat}.")
    return redirect("detail_fournisseur", pk=fournisseur.pk)
