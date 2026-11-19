from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from core.models import JournalAudit
from core.utils import journaliser

from .decorators import ADMIN, role_required
from .forms import CreationUtilisateurForm, UtilisateurForm
from .models import Utilisateur


@role_required(ADMIN)
def liste_utilisateurs(request):
    utilisateurs = Utilisateur.objects.order_by("username")
    return render(
        request,
        "utilisateurs/liste.html",
        {"utilisateurs": utilisateurs},
    )


@role_required(ADMIN)
def creer_utilisateur(request):
    if request.method == "POST":
        form = CreationUtilisateurForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            journaliser(request, "Création d'un utilisateur", utilisateur, utilisateur.username)
            messages.success(request, "Utilisateur créé avec succès.")
            return redirect("liste_utilisateurs")
    else:
        form = CreationUtilisateurForm()
    return render(request, "utilisateurs/form.html", {"form": form, "creation": True})


@role_required(ADMIN)
def modifier_utilisateur(request, pk):
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    if request.method == "POST":
        form = UtilisateurForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            journaliser(request, "Modification d'un utilisateur", utilisateur, utilisateur.username)
            messages.success(request, "Utilisateur mis à jour.")
            return redirect("liste_utilisateurs")
    else:
        form = UtilisateurForm(instance=utilisateur)
    return render(
        request,
        "utilisateurs/form.html",
        {"form": form, "utilisateur": utilisateur},
    )


@role_required(ADMIN)
@require_POST
def basculer_utilisateur(request, pk):
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    if utilisateur.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect("liste_utilisateurs")
    utilisateur.is_active = not utilisateur.is_active
    utilisateur.save(update_fields=["is_active"])
    etat = "activé" if utilisateur.is_active else "désactivé"
    journaliser(request, f"Compte {etat}", utilisateur, utilisateur.username)
    messages.success(request, f"Le compte a été {etat}.")
    return redirect("liste_utilisateurs")


@role_required(ADMIN)
def journal_audit(request):
    entrees = JournalAudit.objects.select_related("utilisateur")
    recherche = request.GET.get("q", "").strip()
    if recherche:
        entrees = entrees.filter(action__icontains=recherche)
    paginator = Paginator(entrees, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "utilisateurs/journal.html",
        {"page": page, "entrees": page.object_list, "recherche": recherche},
    )
