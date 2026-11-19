from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from medicaments.forms import MedicamentForm
from medicaments.models import Categorie, Medicament
from utilisateurs.models import Utilisateur


class MedicamentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom="Paracétamol",
            categorie=cls.categorie,
            code_barres="123456",
            prix_achat=Decimal("300"),
            prix_vente=Decimal("500"),
        )
        cls.caissier = Utilisateur.objects.create_user(
            username="caissier", password="test12345", role="CAISSIER"
        )
        cls.admin = Utilisateur.objects.create_user(
            username="admin", password="test12345", role="ADMIN", is_staff=True
        )

    def test_code_barres_unique(self):
        form = MedicamentForm(
            data={
                "nom": "Ibuprofène",
                "categorie": self.categorie.pk,
                "forme": "COMPRIME",
                "code_barres": "123456",
                "prix_achat": "100",
                "prix_vente": "200",
                "seuil_alerte": "5",
                "statut": "ACTIF",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("code_barres", form.errors)

    def test_prix_vente_inferieur_refuse(self):
        form = MedicamentForm(
            data={
                "nom": "Test",
                "categorie": self.categorie.pk,
                "forme": "COMPRIME",
                "prix_achat": "500",
                "prix_vente": "100",
                "seuil_alerte": "5",
                "statut": "ACTIF",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("prix_vente", form.errors)

    def test_categorie_utilisee_non_supprimable(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(
            reverse("supprimer_categorie", args=[self.categorie.pk])
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Categorie.objects.filter(pk=self.categorie.pk).exists())

    def test_caissier_ne_peut_pas_modifier_medicament(self):
        self.client.force_login(self.caissier)
        reponse = self.client.get(
            reverse("modifier_medicament", args=[self.medicament.pk])
        )
        self.assertEqual(reponse.status_code, 403)

    def test_stock_disponible_exclut_lots_expires(self):
        from datetime import timedelta

        from django.utils import timezone

        from stock.models import LotStock

        LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="VALIDE",
            date_peremption=timezone.localdate() + timedelta(days=300),
            quantite=10,
        )
        LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="PERIME",
            date_peremption=timezone.localdate() - timedelta(days=1),
            quantite=5,
        )
        self.assertEqual(self.medicament.stock_total, 15)
        self.assertEqual(self.medicament.stock_disponible, 10)
        self.assertTrue(self.medicament.est_stock_faible)
