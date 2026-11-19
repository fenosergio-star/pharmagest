from django.urls import path

from . import views

urlpatterns = [
    path("", views.liste_ventes, name="liste_ventes"),
    path("caisse/", views.caisse, name="caisse"),
    path("caisse/ajouter/", views.ajouter_au_panier, name="ajouter_au_panier"),
    path("caisse/panier/", views.panier, name="panier"),
    path("caisse/panier/retirer/<int:lot_id>/", views.retirer_du_panier, name="retirer_du_panier"),
    path("caisse/panier/vider/", views.vider_panier, name="vider_panier"),
    path("<int:pk>/", views.detail_vente, name="detail_vente"),
    path("<int:pk>/retour/", views.retour_vente, name="retour_vente"),
    path("paiement/<int:pk>/confirmer/", views.confirmer_paiement, name="confirmer_paiement"),
]
