from django.urls import path

from . import views

urlpatterns = [
    path("", views.liste_commandes, name="liste_commandes"),
    path("nouvelle/", views.creer_commande, name="creer_commande"),
    path("<int:pk>/", views.detail_commande, name="detail_commande"),
    path("<int:pk>/modifier/", views.modifier_commande, name="modifier_commande"),
    path("<int:pk>/valider/", views.valider_commande, name="valider_commande"),
    path("<int:pk>/annuler/", views.annuler_commande, name="annuler_commande"),
    path("<int:pk>/receptionner/", views.receptionner_commande, name="receptionner_commande"),
]
