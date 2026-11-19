from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("statistiques/", views.statistiques, name="statistiques"),
    path("rapports/vente/<int:pk>/recu.pdf", views.pdf_recu, name="pdf_recu"),
    path("rapports/vente/<int:pk>/facture.pdf", views.pdf_facture, name="pdf_facture"),
    path("rapports/commande/<int:pk>.pdf", views.pdf_bon_commande, name="pdf_bon_commande"),
    path("rapports/reception/<int:pk>.pdf", views.pdf_bon_reception, name="pdf_bon_reception"),
    path("rapports/stock.pdf", views.pdf_rapport_stock, name="pdf_rapport_stock"),
    path("rapports/ventes.pdf", views.pdf_rapport_ventes, name="pdf_rapport_ventes"),
    path("rapports/achats.pdf", views.pdf_rapport_achats, name="pdf_rapport_achats"),
    path("rapports/peremptions.pdf", views.pdf_peremptions, name="pdf_peremptions"),
]
