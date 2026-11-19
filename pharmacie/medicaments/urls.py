from django.urls import path

from . import views

urlpatterns = [
    path("", views.liste_medicaments, name="liste_medicaments"),
    path("nouveau/", views.creer_medicament, name="creer_medicament"),
    path("<int:pk>/", views.detail_medicament, name="detail_medicament"),
    path("<int:pk>/modifier/", views.modifier_medicament, name="modifier_medicament"),
    path("<int:pk>/archiver/", views.archiver_medicament, name="archiver_medicament"),
    path("<int:pk>/supprimer/", views.supprimer_medicament, name="supprimer_medicament"),
    path("categories/", views.liste_categories, name="liste_categories"),
    path("categories/nouvelle/", views.creer_categorie, name="creer_categorie"),
    path("categories/<int:pk>/modifier/", views.modifier_categorie, name="modifier_categorie"),
    path("categories/<int:pk>/supprimer/", views.supprimer_categorie, name="supprimer_categorie"),
]
