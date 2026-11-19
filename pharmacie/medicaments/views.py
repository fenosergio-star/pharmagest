from django.contrib import messages
from django.db.models import ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import journaliser
from utilisateurs.decorators import CAISSIER, GESTIONNAIRE, PHARMACIEN, role_required

from .forms import CategorieForm, MedicamentForm
from .models import Categorie, Medicament

ROLES_LECTURE = (PHARMACIEN, GESTIONNAIRE, CAISSIER)


@role_required(*ROLES_LECTURE)
def liste_medicaments(request):
    medicaments = Medicament.objects.select_related("categorie").annotate(
        stock=Sum("lots__quantite")
    )
    recherche = request.GET.get("q", "").strip()
    categorie = request.GET.get("categorie", "")
    statut = request.GET.get("statut", "ACTIF")
    tri = request.GET.get("tri", "nom")

    if recherche:
        medicaments = medicaments.filter(
            Q(nom__icontains=recherche)
            | Q(denomination_generique__icontains=recherche)
            | Q(code_barres__icontains=recherche)
        )
    if categorie:
        medicaments = medicaments.filter(categorie_id=categorie)
    if statut:
        medicaments = medicaments.filter(statut=statut)

    tris_valides = {"nom", "-nom", "prix_vente", "-prix_vente", "stock", "-stock"}
    medicaments = medicaments.order_by(tri if tri in tris_valides else "nom")

    from django.core.paginator import Paginator

    paginator = Paginator(medicaments, 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "medicaments/liste.html",
        {
            "page": page,
            "medicaments": page.object_list,
            "categories": Categorie.objects.all(),
            "recherche": recherche,
            "categorie_selectionnee": categorie,
            "statut_selectionne": statut,
            "tri": tri,
        },
    )


@role_required(*ROLES_LECTURE)
def detail_medicament(request, pk):
    medicament = get_object_or_404(
        Medicament.objects.select_related("categorie"), pk=pk
    )
    return render(
        request,
        "medicaments/detail.html",
        {
            "medicament": medicament,
            "lots": medicament.lots.order_by("date_peremption"),
            "mouvements": medicament.mouvements.select_related("lot", "utilisateur")[:30],
        },
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def creer_medicament(request):
    if request.method == "POST":
        form = MedicamentForm(request.POST, request.FILES)
        if form.is_valid():
            medicament = form.save()
            journaliser(request, "Création d'un médicament", medicament, medicament.nom)
            messages.success(request, "Médicament enregistré.")
            return redirect("detail_medicament", pk=medicament.pk)
    else:
        form = MedicamentForm()
    return render(
        request,
        "medicaments/form.html",
        {"form": form, "titre": "Ajouter un médicament"},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def modifier_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    if request.method == "POST":
        form = MedicamentForm(request.POST, request.FILES, instance=medicament)
        if form.is_valid():
            form.save()
            journaliser(request, "Modification d'un médicament", medicament, medicament.nom)
            messages.success(request, "Médicament mis à jour.")
            return redirect("detail_medicament", pk=medicament.pk)
    else:
        form = MedicamentForm(instance=medicament)
    return render(
        request,
        "medicaments/form.html",
        {"form": form, "medicament": medicament, "titre": "Modifier un médicament"},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
@require_POST
def archiver_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    medicament.statut = Medicament.Statut.ARCHIVE
    medicament.save(update_fields=["statut"])
    journaliser(request, "Archivage d'un médicament", medicament, medicament.nom)
    messages.success(request, "Médicament archivé.")
    return redirect("liste_medicaments")


@role_required(PHARMACIEN, GESTIONNAIRE)
@require_POST
def supprimer_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    try:
        nom = medicament.nom
        medicament.delete()
        journaliser(request, "Suppression d'un médicament", None, nom)
        messages.success(request, "Médicament supprimé.")
    except ProtectedError:
        medicament.statut = Medicament.Statut.ARCHIVE
        medicament.save(update_fields=["statut"])
        messages.warning(
            request,
            "Ce médicament possède un historique : il a été archivé au lieu d'être supprimé.",
        )
    return redirect("liste_medicaments")


@role_required(PHARMACIEN, GESTIONNAIRE)
def liste_categories(request):
    return render(
        request,
        "categories/liste.html",
        {"categories": Categorie.objects.all()},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
def creer_categorie(request):
    if request.method == "POST":
        form = CategorieForm(request.POST)
        if form.is_valid():
            categorie = form.save()
            journaliser(request, "Création d'une catégorie", categorie, categorie.nom)
            messages.success(request, "Catégorie créée.")
            return redirect("liste_categories")
    else:
        form = CategorieForm()
    return render(request, "categories/form.html", {"form": form, "titre": "Ajouter une catégorie"})


@role_required(PHARMACIEN, GESTIONNAIRE)
def modifier_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == "POST":
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            journaliser(request, "Modification d'une catégorie", categorie, categorie.nom)
            messages.success(request, "Catégorie mise à jour.")
            return redirect("liste_categories")
    else:
        form = CategorieForm(instance=categorie)
    return render(
        request,
        "categories/form.html",
        {"form": form, "categorie": categorie, "titre": "Modifier une catégorie"},
    )


@role_required(PHARMACIEN, GESTIONNAIRE)
@require_POST
def supprimer_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    try:
        categorie.delete()
        journaliser(request, "Suppression d'une catégorie", None, categorie.nom)
        messages.success(request, "Catégorie supprimée.")
    except ProtectedError:
        messages.error(
            request,
            "Impossible de supprimer une catégorie utilisée par des médicaments.",
        )
    return redirect("liste_categories")
