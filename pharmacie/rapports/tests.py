from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from medicaments.models import Categorie, Medicament
from stock.models import LotStock
from utilisateurs.models import Utilisateur
from ventes.services import valider_vente


class RapportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {}
        for nom, role in [
            ("admin", "ADMIN"),
            ("pharmacien", "PHARMACIEN"),
            ("gestionnaire", "GESTIONNAIRE"),
            ("caissier", "CAISSIER"),
            ("responsable", "RESPONSABLE"),
        ]:
            cls.roles[nom] = Utilisateur.objects.create_user(
                username=nom, password="test12345", role=role
            )
        cls.categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom="Paracétamol",
            categorie=cls.categorie,
            prix_achat=Decimal("300"),
            prix_vente=Decimal("500"),
        )
        cls.lot = LotStock.objects.create(
            medicament=cls.medicament,
            numero_lot="LOT-001",
            date_peremption=timezone.localdate() + timedelta(days=10),
            quantite=20,
        )
        cls.vente = valider_vente(
            utilisateur=cls.roles["caissier"],
            mode_paiement="ESPECES",
            lignes=[{"lot_id": cls.lot.pk, "quantite": 2}],
        )

    def test_dashboard_accessible_a_tous_les_roles(self):
        for utilisateur in self.roles.values():
            self.client.force_login(utilisateur)
            reponse = self.client.get(reverse("dashboard"))
            self.assertEqual(reponse.status_code, 200, utilisateur.username)

    def test_page_statistiques(self):
        self.client.force_login(self.roles["responsable"])
        reponse = self.client.get(reverse("statistiques"))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Chiffre d'affaires")

    def test_recu_pdf(self):
        self.client.force_login(self.roles["caissier"])
        reponse = self.client.get(reverse("pdf_recu", args=[self.vente.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertGreater(len(reponse.content), 500)

    def test_facture_pdf(self):
        self.client.force_login(self.roles["caissier"])
        reponse = self.client.get(reverse("pdf_facture", args=[self.vente.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Content-Type"], "application/pdf")

    def test_rapports_pdf_reserves(self):
        self.client.force_login(self.roles["caissier"])
        self.assertEqual(self.client.get(reverse("pdf_rapport_stock")).status_code, 403)
        self.client.force_login(self.roles["responsable"])
        for nom in [
            "pdf_rapport_stock",
            "pdf_rapport_ventes",
            "pdf_rapport_achats",
            "pdf_peremptions",
        ]:
            reponse = self.client.get(reverse(nom))
            self.assertEqual(reponse.status_code, 200, nom)
            self.assertEqual(reponse["Content-Type"], "application/pdf")

    def test_acces_anonyme_redirige(self):
        reponse = self.client.get(reverse("dashboard"))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/comptes/connexion/", reponse["Location"])
