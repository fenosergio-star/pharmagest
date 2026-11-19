from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from fournisseurs.models import Fournisseur
from medicaments.models import Categorie, Medicament
from stock.models import LotStock, MouvementStock
from utilisateurs.models import Utilisateur

from .models import CommandeAchat, LigneAchat


class AchatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Utilisateur.objects.create_user(
            username="admin", password="test12345", role="ADMIN"
        )
        cls.caissier = Utilisateur.objects.create_user(
            username="caissier", password="test12345", role="CAISSIER"
        )
        cls.categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom="Paracétamol",
            categorie=cls.categorie,
            prix_achat=Decimal("300"),
            prix_vente=Decimal("500"),
        )
        cls.fournisseur = Fournisseur.objects.create(nom="Fournisseur Test")
        cls.commande = CommandeAchat.objects.create(
            fournisseur=cls.fournisseur, utilisateur=cls.admin
        )
        cls.ligne = LigneAchat.objects.create(
            commande=cls.commande,
            medicament=cls.medicament,
            quantite=20,
            prix_achat=Decimal("300"),
        )

    def test_commande_ne_modifie_pas_le_stock(self):
        self.assertEqual(LotStock.objects.count(), 0)
        self.assertEqual(self.medicament.stock_total, 0)

    def test_validation_commande_ne_modifie_pas_le_stock(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("valider_commande", args=[self.commande.pk]))
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.COMMANDEE)
        self.assertEqual(self.medicament.stock_total, 0)

    def test_reception_augmente_le_stock_une_seule_fois(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("valider_commande", args=[self.commande.pk]))
        url = reverse("receptionner_commande", args=[self.commande.pk])
        reponse = self.client.post(
            url,
            {
                "notes": "Réception test",
                f"qte_{self.ligne.pk}": "20",
                f"lot_{self.ligne.pk}": "LOT-001",
                f"peremption_{self.ligne.pk}": (
                    timezone.localdate() + timedelta(days=365)
                ).isoformat(),
            },
        )
        self.assertEqual(reponse.status_code, 302)
        self.commande.refresh_from_db()
        self.ligne.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.RECEPTIONNEE)
        self.assertEqual(self.ligne.quantite_recue, 20)
        self.assertEqual(self.medicament.stock_total, 20)
        self.assertEqual(
            MouvementStock.objects.filter(
                medicament=self.medicament, type=MouvementStock.Type.ENTREE
            ).count(),
            1,
        )

        # Une seconde réception ne doit pas augmenter le stock.
        self.client.post(
            url,
            {
                "notes": "",
                f"qte_{self.ligne.pk}": "20",
                f"lot_{self.ligne.pk}": "LOT-002",
                f"peremption_{self.ligne.pk}": (
                    timezone.localdate() + timedelta(days=365)
                ).isoformat(),
            },
        )
        self.medicament.refresh_from_db()
        self.assertEqual(self.medicament.stock_total, 20)

    def test_reception_partielle(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("valider_commande", args=[self.commande.pk]))
        self.client.post(
            reverse("receptionner_commande", args=[self.commande.pk]),
            {
                "notes": "",
                f"qte_{self.ligne.pk}": "5",
                f"lot_{self.ligne.pk}": "LOT-PARTIEL",
                f"peremption_{self.ligne.pk}": (
                    timezone.localdate() + timedelta(days=365)
                ).isoformat(),
            },
        )
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.PARTIELLE)
        self.assertEqual(self.medicament.stock_total, 5)

    def test_caissier_sans_permission(self):
        self.client.force_login(self.caissier)
        reponse = self.client.get(reverse("liste_commandes"))
        self.assertEqual(reponse.status_code, 403)
