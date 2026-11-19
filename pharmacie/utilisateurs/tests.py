from django.test import TestCase
from django.urls import reverse

from .models import Utilisateur


class UtilisateurTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Utilisateur.objects.create_user(
            username="admin", password="test12345", role="ADMIN", is_staff=True
        )
        cls.caissier = Utilisateur.objects.create_user(
            username="caissier", password="test12345", role="CAISSIER"
        )

    def test_page_connexion_accessible(self):
        reponse = self.client.get(reverse("login"))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "PharmaGest")

    def test_connexion_valide(self):
        reponse = self.client.post(
            reverse("login"),
            {"username": "admin", "password": "test12345"},
        )
        self.assertEqual(reponse.status_code, 302)

    def test_liste_utilisateurs_reservee_admin(self):
        self.client.force_login(self.caissier)
        self.assertEqual(self.client.get(reverse("liste_utilisateurs")).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("liste_utilisateurs")).status_code, 200)

    def test_desactivation_compte(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("basculer_utilisateur", args=[self.caissier.pk]))
        self.caissier.refresh_from_db()
        self.assertFalse(self.caissier.is_active)
        self.client.post(reverse("basculer_utilisateur", args=[self.caissier.pk]))
        self.caissier.refresh_from_db()
        self.assertTrue(self.caissier.is_active)

    def test_impossible_desactiver_son_propre_compte(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("basculer_utilisateur", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
