from django.urls import path

from . import views

urlpatterns = [
    path("utilisateurs/", views.liste_utilisateurs, name="liste_utilisateurs"),
    path("utilisateurs/nouveau/", views.creer_utilisateur, name="creer_utilisateur"),
    path("utilisateurs/<int:pk>/modifier/", views.modifier_utilisateur, name="modifier_utilisateur"),
    path("utilisateurs/<int:pk>/basculer/", views.basculer_utilisateur, name="basculer_utilisateur"),
    path("journal-audit/", views.journal_audit, name="journal_audit"),
]
