from django.urls import path

from . import views

urlpatterns = [
    path("", views.liste_fournisseurs, name="liste_fournisseurs"),
    path("nouveau/", views.creer_fournisseur, name="creer_fournisseur"),
    path("<int:pk>/", views.detail_fournisseur, name="detail_fournisseur"),
    path("<int:pk>/modifier/", views.modifier_fournisseur, name="modifier_fournisseur"),
    path("<int:pk>/basculer/", views.basculer_fournisseur, name="basculer_fournisseur"),
]
