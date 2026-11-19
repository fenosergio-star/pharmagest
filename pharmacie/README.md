# PharmaGest — Application web de gestion de pharmacie (Django)

Application complète développée à partir du cahier des charges « Conception et
développement d'une application web de gestion pharmaceutique ». Elle couvre les
médicaments, catégories, fournisseurs, clients, achats, réceptions, lots, stocks,
ventes, paiements, retours, utilisateurs/rôles, tableau de bord et documents PDF.

## Technologies

- Python 3.12, Django 5.2
- SQLite en développement (PostgreSQL recommandé en production)
- Bootstrap 5, HTML5/CSS3
- Pillow (photos des médicaments)
- ReportLab (reçus, factures, bons et rapports PDF)
- Tests avec `django.test.TestCase`

## Installation

```bash
cd /home/sergio/L3/django/pharmacie
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

L'application est disponible sur <http://127.0.0.1:8000/>.

### Comptes de démonstration

| Identifiant | Mot de passe | Rôle |
|---|---|---|
| `admin` | `admin123` | Administrateur (superuser) |
| `pharmacien` | `pharma123` | Pharmacien responsable |
| `gestionnaire` | `stock123` | Gestionnaire de stock |
| `caissier` | `caisse123` | Caissier |
| `responsable` | `gest123` | Responsable de gestion |

> Changez ces mots de passe avant toute utilisation réelle.

## Modules fonctionnels

- **Authentification et utilisateurs** : connexion/déconnexion, changement de mot
  de passe, création/modification de comptes, activation/désactivation, rôles.
- **Médicaments** : CRUD complet, photo, catégorie, forme, dosage, laboratoire,
  code-barres unique, prix, seuil d'alerte, statut actif/archivé. Recherche par
  nom/générique/code-barres, filtrage, tri et pagination. Suppression protégée :
  un médicament avec historique est archivé, pas supprimé.
- **Catégories** : CRUD ; suppression impossible si des médicaments l'utilisent.
- **Fournisseurs** : CRUD, recherche nom/téléphone, historique des achats,
  désactivation sans perte d'historique.
- **Clients** : CRUD, recherche, historique des ventes, vente comptoir sans client.
- **Achats** : commande en brouillon avec lignes, validation, annulation,
  réception partielle ou totale. Une commande ne modifie jamais le stock : seule
  la réception effective crée les lots et les mouvements d'entrée.
- **Stock et lots** : lots avec numéro et date de péremption, mouvements traçables
  (entrée, sortie, retour, correction d'inventaire), blocage/déblocage de lot,
  alertes de rupture et de stock faible, péremptions proches, inventaire physique.
- **Ventes / caisse** : recherche par nom ou code-barres, lots proposés en FEFO,
  panier, prix appliqué figé sur la ligne de vente, paiement (espèces, mobile
  money, carte), validation atomique, reçu et facture PDF.
- **Retours** : opération compensatoire traçable, motif, utilisateur, quantité
  contrôlée, remboursement, remise en stock conditionnelle.
- **Tableau de bord et statistiques** : médicaments actifs, ventes du jour,
  stocks faibles, péremptions, chiffre d'affaires, encaissements, remboursements,
  marge commerciale estimée, achats, produits les plus vendus, période choisie.
- **Documents PDF** : reçu de vente, facture, bon de commande, bon de réception,
  rapport de stock, rapport des ventes, rapport des achats, liste des produits
  périmés/proches de la péremption.
- **Journal d'audit** : auteur, date, action, objet, détails et adresse IP des
  opérations sensibles (consultable par l'administrateur et dans l'admin Django).

## Règles de gestion appliquées

- Code-barres unique, prix et quantités validés côté serveur.
- Une commande ne modifie pas le stock ; une réception augmente le stock une
  seule fois ; une vente le diminue une seule fois.
- Le stock ne peut pas devenir négatif ; une vente impossible est refusée.
- Les lots périmés ou bloqués sont exclus de la vente ; FEFO à la caisse.
- Les prix appliqués sont conservés sur les lignes historiques.
- Validation des ventes/réceptions dans une transaction atomique avec verrouillage
  des lots (`select_for_update`).
- Accès aux vues contrôlé par rôle ; les opérations sensibles sont journalisées.
- Retours et annulations ne suppriment pas l'historique.

## Rôles et accès principaux

| Fonction | Admin | Pharmacien | Gestionnaire | Caissier | Responsable |
|---|---|---|---|---|---|
| Utilisateurs / audit | Oui | Non | Non | Non | Non |
| Médicaments / catégories | Oui | Oui | Oui | Lecture | Lecture |
| Stock / lots | Oui | Oui | Oui | Lecture | Lecture |
| Achats / fournisseurs | Oui | Oui | Oui | Non | Non |
| Caisse / ventes / retours | Oui | Oui | Non | Oui | Lecture ventes |
| Rapports et PDF | Oui | Oui | Oui | Reçus/factures | Oui |

L'administrateur (ou superuser) passe toujours les contrôles de rôle.

## Structure du projet

```
pharmacie/
├── manage.py
├── config/            # settings, urls, wsgi/asgi
├── core/              # audit, utilitaires, commandes (seed, sauvegarde)
├── utilisateurs/      # utilisateur personnalisé, rôles, décorateurs
├── medicaments/       # catégories et médicaments
├── fournisseurs/
├── clients/
├── stock/             # lots, mouvements et services de stock
├── achats/            # commandes, lignes, réceptions
├── ventes/            # ventes, lignes, paiements, retours et services
├── rapports/          # tableau de bord, statistiques, PDF ReportLab
├── templates/         # interface Bootstrap
├── static/css/        # styles
├── media/             # photos uploadées
└── requirements.txt
```

## Tests

```bash
python manage.py test
```

Les 32 tests couvrent notamment : unicité du code-barres, protection des
catégories, prix, permissions, réception unique du stock, réception partielle,
vente atomique, stock insuffisant, lot périmé, retour et remboursement, prix
historique, dashboard et génération PDF.

## Sauvegarde et restauration

Sauvegarde SQLite :

```bash
python manage.py sauvegarder_base
```

Restauration : arrêter le serveur puis copier le fichier souhaité du dossier
`backups/` vers `db.sqlite3`. En production PostgreSQL, utiliser `pg_dump` /
`pg_restore` et tester régulièrement la restauration.

## Mise en production (rappels)

- Définir `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` via des
  variables d'environnement (aucun secret dans le code).
- Utiliser PostgreSQL, HTTPS, un serveur WSGI/ASGI et un reverse proxy.
- Configurer des sauvegardes protégées et testées.
- Vérifier les obligations locales (délivrance, lots, factures, données
  personnelles, paiements) avant toute exploitation réelle.

## Limites du périmètre

L'application ne réalise pas de diagnostic médical, de prescription automatique,
de consultation médicale, de fabrication industrielle ni de comptabilité générale
complète. Elle ne remplace pas les obligations réglementaires d'une pharmacie
réelle.
