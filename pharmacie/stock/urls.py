from django.urls import path

from . import views

urlpatterns = [
    path("", views.liste_stock, name="liste_stock"),
    path("lots/", views.liste_lots, name="liste_lots"),
    path("mouvements/", views.liste_mouvements, name="liste_mouvements"),
    path("peremptions/", views.liste_peremptions, name="liste_peremptions"),
    path("lots/<int:pk>/corriger/", views.corriger_lot, name="corriger_lot"),
    path("lots/<int:pk>/basculer/", views.basculer_lot, name="basculer_lot"),
]
