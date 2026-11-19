from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import journaliser
from utilisateurs.decorators import CAISSIER, PHARMACIEN, role_required

from .forms import ClientForm
from .models import Client


@role_required(PHARMACIEN, CAISSIER)
def liste_clients(request):
    clients = Client.objects.all()
    recherche = request.GET.get("q", "").strip()
    if recherche:
        clients = clients.filter(
            Q(nom__icontains=recherche) | Q(telephone__icontains=recherche)
        )
    return render(
        request,
        "clients/liste.html",
        {"clients": clients, "recherche": recherche},
    )


@role_required(PHARMACIEN, CAISSIER)
def detail_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    ventes = client.ventes.select_related("utilisateur").order_by("-date_vente")
    return render(
        request,
        "clients/detail.html",
        {"client": client, "ventes": ventes},
    )


@role_required(PHARMACIEN, CAISSIER)
def creer_client(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            journaliser(request, "Création d'un client", client, client.nom)
            messages.success(request, "Client créé.")
            return redirect("detail_client", pk=client.pk)
    else:
        form = ClientForm()
    return render(request, "clients/form.html", {"form": form, "titre": "Ajouter un client"})


@role_required(PHARMACIEN, CAISSIER)
def modifier_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            journaliser(request, "Modification d'un client", client, client.nom)
            messages.success(request, "Client mis à jour.")
            return redirect("detail_client", pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(
        request,
        "clients/form.html",
        {"form": form, "client": client, "titre": "Modifier un client"},
    )


@role_required(PHARMACIEN, CAISSIER)
@require_POST
def basculer_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    client.actif = not client.actif
    client.save(update_fields=["actif"])
    etat = "activé" if client.actif else "désactivé"
    journaliser(request, f"Client {etat}", client, client.nom)
    messages.success(request, f"Client {etat}.")
    return redirect("detail_client", pk=client.pk)
