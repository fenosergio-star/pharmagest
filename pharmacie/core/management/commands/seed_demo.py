"""Jeu de données fictives pour tester PharmaGest."""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from clients.models import Client
from fournisseurs.models import Fournisseur
from medicaments.models import Categorie, Medicament
from stock.models import LotStock
from stock.services import entrer_stock
from utilisateurs.models import Utilisateur
from ventes.models import Vente
from ventes.services import valider_vente


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (utilisateurs, médicaments, lots, ventes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les données de démonstration existantes avant de recréer.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Suppression des données existantes...")
            Vente.objects.all().delete()
            Medicament.objects.all().delete()
            Categorie.objects.all().delete()
            Fournisseur.objects.all().delete()
            Client.objects.all().delete()

        utilisateurs = self.creer_utilisateurs()
        self.creer_groupes()
        self.creer_catalogue(utilisateurs)
        self.stdout.write(self.style.SUCCESS("Jeu de données de démonstration prêt."))

    def creer_utilisateurs(self):
        comptes = [
            ("admin", "admin123", "ADMIN", "Administrateur", True),
            ("pharmacien", "pharma123", "PHARMACIEN", "Pharmacien", False),
            ("gestionnaire", "stock123", "GESTIONNAIRE", "Gestionnaire", False),
            ("caissier", "caisse123", "CAISSIER", "Caissier", False),
            ("responsable", "gest123", "RESPONSABLE", "Responsable", False),
        ]
        resultat = {}
        for username, mot_de_passe, role, prenom, admin in comptes:
            utilisateur, cree = Utilisateur.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": prenom,
                    "last_name": "Demo",
                    "role": role,
                    "is_staff": admin or role == "ADMIN",
                    "is_superuser": admin,
                    "email": f"{username}@pharmagest.mg",
                },
            )
            if cree:
                utilisateur.set_password(mot_de_passe)
                if admin:
                    utilisateur.is_staff = True
                    utilisateur.is_superuser = True
                utilisateur.save()
            resultat[username] = utilisateur
        self.stdout.write("Utilisateurs : admin/admin123, pharmacien/pharma123, "
                          "gestionnaire/stock123, caissier/caisse123, responsable/gest123")
        return resultat

    def creer_groupes(self):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        from achats.models import CommandeAchat, ReceptionAchat
        from medicaments.models import Medicament
        from stock.models import LotStock, MouvementStock

        groupes = {
            "Pharmacien": [Medicament, Categorie, LotStock, MouvementStock, CommandeAchat, ReceptionAchat],
            "Gestionnaire de stock": [Medicament, Categorie, LotStock, MouvementStock, CommandeAchat, ReceptionAchat],
            "Caissier": [Medicament, Client],
            "Responsable de gestion": [],
        }
        for nom, modeles in groupes.items():
            groupe, _ = Group.objects.get_or_create(name=nom)
            permissions = []
            for modele in modeles:
                type_contenu = ContentType.objects.get_for_model(modele)
                permissions.extend(
                    Permission.objects.filter(content_type=type_contenu).exclude(
                        codename__startswith="delete_"
                    )
                )
            groupe.permissions.set(permissions)

    def creer_catalogue(self, utilisateurs):
        if Medicament.objects.exists():
            self.stdout.write("Catalogue déjà présent : création des lots/ventes ignorée.")
            return

        categories = {
            nom: Categorie.objects.create(nom=nom, description=f"Catégorie {nom.lower()}")
            for nom in [
                "Antalgiques",
                "Antibiotiques",
                "Vitamines",
                "Antiseptiques",
                "Gastro-entérologie",
            ]
        }

        fournisseurs = [
            Fournisseur.objects.create(
                nom="Laboratoires Océan Indien",
                adresse="Zone industrielle Forello, Antananarivo",
                telephone="+261 20 22 000 01",
                email="contact@loi.mg",
                contact_principal="M. Rakoto",
                numero_fiscal="NIF 123456789",
            ),
            Fournisseur.objects.create(
                nom="Pharma Distribution",
                adresse="Rue Rainibetsimisaraka, Antananarivo",
                telephone="+261 20 22 000 02",
                email="ventes@pharmadist.mg",
                contact_principal="Mme Rasoa",
            ),
            Fournisseur.objects.create(
                nom="MedSupply Madagascar",
                adresse="Toamasina",
                telephone="+261 20 22 000 03",
                email="info@medsupply.mg",
                contact_principal="M. Jean",
            ),
        ]

        clients = [
            Client.objects.create(nom="Rakoto Andry", telephone="034 12 345 67"),
            Client.objects.create(nom="Rabe Lalao", telephone="033 98 765 43", email="lalao@example.mg"),
            Client.objects.create(nom="Association Santé Plus", telephone="020 22 555 01"),
        ]

        medicaments = [
            ("Paracétamol", "Paracétamol", "Antalgiques", "COMPRIME", "500 mg", "Pharmalab", 300, 500, 20),
            ("Ibuprofène", "Ibuprofène", "Antalgiques", "COMPRIME", "400 mg", "Pharmalab", 400, 700, 15),
            ("Amoxicilline", "Amoxicilline", "Antibiotiques", "GELULE", "500 mg", "Océan Lab", 1200, 2000, 10),
            ("Azithromycine", "Azithromycine", "Antibiotiques", "COMPRIME", "250 mg", "Océan Lab", 1500, 2500, 8),
            ("Vitamine C", "Acide ascorbique", "Vitamines", "COMPRIME", "1000 mg", "VitaPlus", 200, 400, 25),
            ("Vitamine D3", "Cholécalciférol", "Vitamines", "GELULE", "1000 UI", "VitaPlus", 500, 900, 12),
            ("Bétadine", "Povidone iodée", "Antiseptiques", "AUTRE", "10 %", "Medica", 800, 1300, 10),
            ("Alcool 70°", "Éthanol", "Antiseptiques", "AUTRE", "70 %", "Medica", 300, 600, 20),
            ("Oméprazole", "Oméprazole", "Gastro-entérologie", "GELULE", "20 mg", "GastroLab", 600, 1100, 15),
            ("Smecta", "Diosmectite", "Gastro-entérologie", "AUTRE", "3 g", "GastroLab", 700, 1200, 12),
        ]
        objets = []
        for i, (nom, generique, cat, forme, dosage, labo, achat, vente, seuil) in enumerate(medicaments, start=1):
            objets.append(
                Medicament.objects.create(
                    nom=nom,
                    denomination_generique=generique,
                    categorie=categories[cat],
                    forme=forme,
                    dosage=dosage,
                    laboratoire=labo,
                    code_barres=f"MG{i:06d}",
                    prix_achat=Decimal(achat),
                    prix_vente=Decimal(vente),
                    seuil_alerte=seuil,
                )
            )

        aujourdhui = timezone.localdate()
        utilisateur = utilisateurs["gestionnaire"]
        for i, medicament in enumerate(objets):
            entrer_stock(
                medicament,
                f"LOT-{aujourdhui:%Y}-{i + 1:03d}",
                aujourdhui + timedelta(days=400 + i * 15),
                40 + i * 3,
                utilisateur=utilisateur,
                motif="Stock initial de démonstration",
                reference="SEED",
            )
        # Un lot proche de la péremption et un lot périmé.
        entrer_stock(
            objets[0], "LOT-PROCHE-001", aujourdhui + timedelta(days=12), 15,
            utilisateur=utilisateur, motif="Démonstration péremption proche", reference="SEED",
        )
        entrer_stock(
            objets[1], "LOT-PERIME-001", aujourdhui - timedelta(days=5), 10,
            utilisateur=utilisateur, motif="Démonstration lot périmé", reference="SEED",
        )
        lot_bloque = LotStock.objects.filter(medicament=objets[8]).first()
        if lot_bloque:
            lot_bloque.bloque = True
            lot_bloque.save(update_fields=["bloque"])

        caissier = utilisateurs["caissier"]
        for i in range(3):
            lots = list(
                objets[i].lots.filter(date_peremption__gte=aujourdhui, bloque=False)
                .order_by("date_peremption")[:1]
            )
            if lots:
                valider_vente(
                    utilisateur=caissier,
                    mode_paiement="ESPECES",
                    lignes=[{"lot_id": lots[0].pk, "quantite": 2}],
                    client=clients[i % len(clients)],
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(categories)} catégories, {len(medicaments)} médicaments, "
                f"{len(fournisseurs)} fournisseurs et quelques ventes créés."
            )
        )
