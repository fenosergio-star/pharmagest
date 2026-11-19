from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from medicaments.models import Categorie, Medicament
from stock.models import LotStock, MouvementStock
from stock.services import StockError, corriger_stock, entrer_stock
from utilisateurs.models import Utilisateur
from ventes.models import LigneVente, Vente
from ventes.services import enregistrer_retour, valider_vente


class VenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        cls.lot = LotStock.objects.create(
            medicament=cls.medicament,
            numero_lot="LOT-VALIDE",
            date_peremption=timezone.localdate() + timedelta(days=365),
            quantite=10,
        )
        cls.lot_perime = LotStock.objects.create(
            medicament=cls.medicament,
            numero_lot="LOT-PERIME",
            date_peremption=timezone.localdate() - timedelta(days=1),
            quantite=10,
        )

    def test_vente_diminue_le_stock_une_seule_fois(self):
        vente = valider_vente(
            utilisateur=self.caissier,
            mode_paiement="ESPECES",
            lignes=[{"lot_id": self.lot.pk, "quantite": 3}],
        )
        self.lot.refresh_from_db()
        self.medicament.refresh_from_db()
        self.assertIsInstance(vente, Vente)
        self.assertEqual(self.lot.quantite, 7)
        self.assertEqual(self.medicament.stock_total, 17)
        self.assertEqual(vente.lignes.count(), 1)
        self.assertEqual(vente.total, Decimal("1500.00"))
        self.assertEqual(
            MouvementStock.objects.filter(
                medicament=self.medicament, type=MouvementStock.Type.SORTIE
            ).count(),
            1,
        )
        self.assertEqual(vente.paiements.count(), 1)

    def test_vente_stock_insuffisant_refusee(self):
        with self.assertRaises(StockError):
            valider_vente(
                utilisateur=self.caissier,
                mode_paiement="ESPECES",
                lignes=[{"lot_id": self.lot.pk, "quantite": 11}],
            )
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 10)
        self.assertEqual(Vente.objects.count(), 0)

    def test_vente_lot_perime_refusee(self):
        with self.assertRaises(StockError):
            valider_vente(
                utilisateur=self.caissier,
                mode_paiement="ESPECES",
                lignes=[{"lot_id": self.lot_perime.pk, "quantite": 1}],
            )
        self.assertEqual(Vente.objects.count(), 0)

    def test_vente_quantite_negative_refusee(self):
        with self.assertRaises(StockError):
            valider_vente(
                utilisateur=self.caissier,
                mode_paiement="ESPECES",
                lignes=[{"lot_id": self.lot.pk, "quantite": -2}],
            )
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 10)

    def test_vente_est_atomique_si_une_ligne_echoue(self):
        autre_lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="LOT-PETIT",
            date_peremption=timezone.localdate() + timedelta(days=100),
            quantite=1,
        )
        with self.assertRaises(StockError):
            valider_vente(
                utilisateur=self.caissier,
                mode_paiement="ESPECES",
                lignes=[
                    {"lot_id": self.lot.pk, "quantite": 2},
                    {"lot_id": autre_lot.pk, "quantite": 5},
                ],
            )
        self.lot.refresh_from_db()
        autre_lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 10)
        self.assertEqual(autre_lot.quantite, 1)
        self.assertEqual(Vente.objects.count(), 0)

    def test_retour_reintegre_le_stock(self):
        vente = valider_vente(
            utilisateur=self.caissier,
            mode_paiement="ESPECES",
            lignes=[{"lot_id": self.lot.pk, "quantite": 4}],
        )
        ligne = vente.lignes.first()
        retour = enregistrer_retour(
            vente=vente,
            ligne_vente=ligne,
            quantite=2,
            motif="Produit non utilisé",
            utilisateur=self.caissier,
        )
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 8)
        self.assertEqual(retour.montant_rembourse, Decimal("1000.00"))
        self.assertEqual(vente.montant_rembourse, Decimal("1000.00"))

    def test_retour_superieur_au_vendu_refuse(self):
        vente = valider_vente(
            utilisateur=self.caissier,
            mode_paiement="ESPECES",
            lignes=[{"lot_id": self.lot.pk, "quantite": 2}],
        )
        with self.assertRaises(StockError):
            enregistrer_retour(
                vente=vente,
                ligne_vente=vente.lignes.first(),
                quantite=3,
                motif="Trop",
                utilisateur=self.caissier,
            )

    def test_paiement_mobile_sans_reference_en_attente_puis_confirme(self):
        vente = valider_vente(
            utilisateur=self.caissier,
            mode_paiement="MOBILE_MONEY",
            lignes=[{"lot_id": self.lot.pk, "quantite": 1}],
        )
        paiement = vente.paiements.get()
        self.assertEqual(paiement.statut, "EN_ATTENTE")

        self.client.force_login(self.caissier)
        reponse = self.client.post(
            reverse("confirmer_paiement", args=[paiement.pk]),
            {"reference": "TX-123"},
        )
        self.assertEqual(reponse.status_code, 302)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, "CONFIRME")
        self.assertEqual(paiement.reference, "TX-123")

    def test_prix_applique_conserve_apres_modification(self):
        vente = valider_vente(
            utilisateur=self.caissier,
            mode_paiement="ESPECES",
            lignes=[{"lot_id": self.lot.pk, "quantite": 1}],
        )
        self.medicament.prix_vente = Decimal("999")
        self.medicament.save(update_fields=["prix_vente"])
        ligne = vente.lignes.first()
        self.assertEqual(ligne.prix_unitaire, Decimal("500"))
        self.assertEqual(vente.total, Decimal("500.00"))


class StockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = Utilisateur.objects.create_user(
            username="gestionnaire", password="test12345", role="GESTIONNAIRE"
        )
        cls.categorie = Categorie.objects.create(nom="Vitamines")
        cls.medicament = Medicament.objects.create(
            nom="Vitamine C",
            categorie=cls.categorie,
            prix_achat=Decimal("200"),
            prix_vente=Decimal("400"),
        )

    def test_entree_cree_lot_et_mouvement(self):
        lot = entrer_stock(
            self.medicament,
            "LOT-ENTREE",
            timezone.localdate() + timedelta(days=200),
            15,
            utilisateur=self.utilisateur,
        )
        self.assertEqual(lot.quantite, 15)
        self.assertEqual(
            MouvementStock.objects.filter(
                lot=lot, type=MouvementStock.Type.ENTREE, quantite=15
            ).count(),
            1,
        )

    def test_correction_inventaire(self):
        lot = entrer_stock(
            self.medicament,
            "LOT-CORRECTION",
            timezone.localdate() + timedelta(days=200),
            15,
            utilisateur=self.utilisateur,
        )
        corriger_stock(lot, 12, utilisateur=self.utilisateur, motif="Inventaire")
        lot.refresh_from_db()
        self.assertEqual(lot.quantite, 12)
        mouvement = MouvementStock.objects.filter(
            lot=lot, type=MouvementStock.Type.CORRECTION
        ).latest("id")
        self.assertEqual(mouvement.quantite, -3)
