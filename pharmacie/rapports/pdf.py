"""Génération des documents PDF avec ReportLab."""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLEU = colors.HexColor("#0d6efd")
GRIS = colors.HexColor("#f2f4f7")
GRIS_FONCE = colors.HexColor("#495057")
ROUGE = colors.HexColor("#dc3545")


def ariary(montant):
    try:
        montant = Decimal(montant)
    except Exception:
        montant = Decimal("0")
    return f"{montant:,.2f} Ar".replace(",", " ")


def _styles():
    styles = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle(
            "TitreDoc", parent=styles["Title"], fontSize=16, spaceAfter=2
        ),
        "sous_titre": ParagraphStyle(
            "SousTitre", parent=styles["Normal"], fontSize=9, textColor=GRIS_FONCE
        ),
        "normal": ParagraphStyle("NormalDoc", parent=styles["Normal"], fontSize=9),
        "petit": ParagraphStyle("Petit", parent=styles["Normal"], fontSize=8),
        "droite": ParagraphStyle(
            "Droite", parent=styles["Normal"], fontSize=9, alignment=TA_RIGHT
        ),
        "centre": ParagraphStyle(
            "Centre", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER
        ),
        "h2": ParagraphStyle(
            "H2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4
        ),
    }


def _pied_de_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS_FONCE)
    canvas.drawString(15 * mm, 10 * mm, settings.PHARMACIE_NOM)
    canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _entete(titre, reference="", date=None, styles=None):
    styles = styles or _styles()
    date = date or timezone.localtime()
    infos = (
        f"<b>{escape(settings.PHARMACIE_NOM)}</b><br/>"
        f"{escape(settings.PHARMACIE_ADRESSE)}<br/>"
        f"Tél. : {escape(settings.PHARMACIE_TELEPHONE)}<br/>"
        f"{escape(settings.PHARMACIE_EMAIL)}<br/>"
        f"{escape(settings.PHARMACIE_NIF)} - {escape(settings.PHARMACIE_STAT)}"
    )
    droite = f"<b>{escape(titre)}</b><br/>"
    if reference:
        droite += f"N° {escape(str(reference))}<br/>"
    droite += f"Date : {date:%d/%m/%Y %H:%M}"
    tableau = Table(
        [
            [Paragraph(infos, styles["petit"]), Paragraph(droite, styles["droite"])],
        ],
        colWidths=[95 * mm, 85 * mm],
    )
    tableau.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, BLEU),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tableau


def _tableau(donnees, largeurs, styles=None, entete=True, alignements=None):
    styles = styles or _styles()
    tableau = Table(donnees, colWidths=largeurs, repeatRows=1 if entete else 0)
    commandes = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ced4da")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if entete:
        commandes += [
            ("BACKGROUND", (0, 0), (-1, 0), BLEU),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
        commandes.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]))
    if alignements:
        for colonne, alignement in alignements.items():
            commandes.append(("ALIGN", (colonne, 0), (colonne, -1), alignement))
    tableau.setStyle(TableStyle(commandes))
    return tableau


def _construire(elements, titre_pied=""):
    tampon = BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=titre_pied or settings.PHARMACIE_NOM,
        author=settings.PHARMACIE_NOM,
    )
    document.build(elements, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
    return tampon.getvalue()


def recu_vente(vente):
    styles = _styles()
    elements = [_entete("REÇU DE VENTE", vente.numero, vente.date_vente, styles), Spacer(1, 6)]
    client = vente.client.nom if vente.client else "Client comptoir"
    elements.append(
        Paragraph(
            f"Client : <b>{escape(client)}</b><br/>"
            f"Caissier : {escape(str(vente.utilisateur or '-'))}<br/>"
            f"Paiement : {vente.get_mode_paiement_display()}",
            styles["normal"],
        )
    )
    elements.append(Spacer(1, 6))
    donnees = [["Désignation", "Lot", "Qté", "Prix unitaire", "Sous-total"]]
    for ligne in vente.lignes.select_related("medicament", "lot"):
        donnees.append(
            [
                Paragraph(escape(str(ligne.medicament)), styles["petit"]),
                escape(ligne.lot.numero_lot if ligne.lot else "-"),
                str(ligne.quantite),
                ariary(ligne.prix_unitaire),
                ariary(ligne.sous_total),
            ]
        )
    donnees.append(["", "", "", "TOTAL", ariary(vente.total)])
    elements.append(
        _tableau(
            donnees,
            [68 * mm, 25 * mm, 15 * mm, 35 * mm, 37 * mm],
            styles,
            alignements={2: "CENTER", 3: "RIGHT", 4: "RIGHT"},
        )
    )
    if vente.montant_rembourse:
        elements.append(Spacer(1, 4))
        elements.append(
            Paragraph(
                f"Retours/remboursements : {ariary(vente.montant_rembourse)} — "
                f"Net : <b>{ariary(vente.net)}</b>",
                styles["droite"],
            )
        )
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("Merci de votre confiance. Conservez ce reçu.", styles["centre"]))
    elements.append(
        Paragraph(
            "Document généré par PharmaGest. Les médicaments ne sont ni repris ni échangés "
            "sans justification et autorisation.",
            styles["petit"],
        )
    )
    return _construire(elements, f"Reçu {vente.numero}")


def facture_vente(vente):
    styles = _styles()
    elements = [_entete("FACTURE", vente.numero, vente.date_vente, styles), Spacer(1, 6)]
    if vente.client:
        client = (
            f"<b>{escape(vente.client.nom)}</b><br/>"
            f"{escape(vente.client.adresse)}<br/>"
            f"Tél. : {escape(vente.client.telephone)}"
        )
    else:
        client = "<b>Client comptoir</b>"
    elements.append(Paragraph(client, styles["normal"]))
    elements.append(Spacer(1, 6))
    donnees = [["Désignation", "Qté", "Prix unitaire", "Sous-total"]]
    for ligne in vente.lignes.select_related("medicament"):
        donnees.append(
            [
                Paragraph(escape(str(ligne.medicament)), styles["petit"]),
                str(ligne.quantite),
                ariary(ligne.prix_unitaire),
                ariary(ligne.sous_total),
            ]
        )
    donnees.append(["", "", "TOTAL TTC", ariary(vente.total)])
    elements.append(
        _tableau(
            donnees,
            [95 * mm, 15 * mm, 35 * mm, 35 * mm],
            styles,
            alignements={1: "CENTER", 2: "RIGHT", 3: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            f"{escape(settings.PHARMACIE_NIF)} — {escape(settings.PHARMACIE_STAT)}<br/>"
            "Facture émise conformément à la réglementation en vigueur.",
            styles["petit"],
        )
    )
    return _construire(elements, f"Facture {vente.numero}")


def bon_commande(commande):
    styles = _styles()
    elements = [
        _entete("BON DE COMMANDE", commande.numero, commande.date_commande, styles),
        Spacer(1, 6),
    ]
    fournisseur = commande.fournisseur
    elements.append(
        Paragraph(
            f"Fournisseur : <b>{escape(fournisseur.nom)}</b><br/>"
            f"{escape(fournisseur.adresse)}<br/>"
            f"Tél. : {escape(fournisseur.telephone)} — {escape(fournisseur.email)}<br/>"
            f"Statut : {commande.get_statut_display()}",
            styles["normal"],
        )
    )
    elements.append(Spacer(1, 6))
    donnees = [["Désignation", "Qté commandée", "Prix d'achat", "Sous-total"]]
    for ligne in commande.lignes.select_related("medicament"):
        donnees.append(
            [
                Paragraph(escape(str(ligne.medicament)), styles["petit"]),
                str(ligne.quantite),
                ariary(ligne.prix_achat),
                ariary(ligne.sous_total),
            ]
        )
    donnees.append(["", "", "TOTAL", ariary(commande.total)])
    elements.append(
        _tableau(
            donnees,
            [95 * mm, 25 * mm, 30 * mm, 30 * mm],
            styles,
            alignements={1: "CENTER", 2: "RIGHT", 3: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph(
            "Signature du fournisseur<br/><br/>____________________________",
            styles["normal"],
        )
    )
    return _construire(elements, f"Commande {commande.numero}")


def bon_reception(reception):
    styles = _styles()
    commande = reception.commande
    elements = [
        _entete("BON DE RÉCEPTION", reception.numero, reception.date_reception, styles),
        Spacer(1, 6),
    ]
    elements.append(
        Paragraph(
            f"Commande : <b>{commande.numero}</b><br/>"
            f"Fournisseur : {escape(commande.fournisseur.nom)}<br/>"
            f"Réceptionné par : {escape(str(reception.utilisateur or '-'))}",
            styles["normal"],
        )
    )
    elements.append(Spacer(1, 6))
    donnees = [["Désignation", "Lot", "Péremption", "Qté reçue", "Prix d'achat", "Sous-total"]]
    for ligne in reception.lignes.select_related("ligne_achat__medicament"):
        donnees.append(
            [
                Paragraph(escape(str(ligne.ligne_achat.medicament)), styles["petit"]),
                escape(ligne.numero_lot),
                ligne.date_peremption.strftime("%d/%m/%Y"),
                str(ligne.quantite),
                ariary(ligne.ligne_achat.prix_achat),
                ariary(ligne.sous_total),
            ]
        )
    donnees.append(["", "", "", "", "TOTAL", ariary(reception.montant)])
    elements.append(
        _tableau(
            donnees,
            [55 * mm, 25 * mm, 25 * mm, 18 * mm, 28 * mm, 29 * mm],
            styles,
            alignements={3: "CENTER", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    return _construire(elements, f"Réception {reception.numero}")


def rapport_stock(lots):
    styles = _styles()
    elements = [_entete("RAPPORT DE STOCK", date=timezone.localtime(), styles=styles), Spacer(1, 6)]
    donnees = [["Médicament", "Lot", "Péremption", "Quantité", "Statut"]]
    total = 0
    for lot in lots:
        total += lot.quantite
        if lot.bloque:
            statut = "Bloqué"
        elif lot.est_perime:
            statut = "Périmé"
        elif lot.quantite == 0:
            statut = "Épuisé"
        else:
            statut = "Disponible"
        donnees.append(
            [
                Paragraph(escape(str(lot.medicament)), styles["petit"]),
                escape(lot.numero_lot),
                lot.date_peremption.strftime("%d/%m/%Y"),
                str(lot.quantite),
                statut,
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [70 * mm, 30 * mm, 28 * mm, 22 * mm, 30 * mm],
            styles,
            alignements={3: "CENTER"},
        )
    )
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>Total des unités en stock : {total}</b>", styles["droite"]))
    return _construire(elements, "Rapport de stock")


def rapport_ventes(ventes, debut, fin):
    styles = _styles()
    elements = [
        _entete("RAPPORT DES VENTES", f"du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}", styles=styles),
        Spacer(1, 6),
    ]
    donnees = [["N°", "Date", "Client", "Paiement", "Total", "Remboursé", "Net"]]
    total = rembourse = 0
    for vente in ventes:
        total += vente.total
        rembourse += vente.montant_rembourse
        donnees.append(
            [
                vente.numero,
                timezone.localtime(vente.date_vente).strftime("%d/%m/%Y %H:%M"),
                Paragraph(escape(vente.client.nom if vente.client else "Comptoir"), styles["petit"]),
                vente.get_mode_paiement_display(),
                ariary(vente.total),
                ariary(vente.montant_rembourse),
                ariary(vente.net),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [32 * mm, 30 * mm, 35 * mm, 25 * mm, 22 * mm, 20 * mm, 21 * mm],
            styles,
            alignements={4: "RIGHT", 5: "RIGHT", 6: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 6))
    elements.append(
        Paragraph(
            f"<b>{len(ventes)} vente(s)</b> — Chiffre d'affaires : {ariary(total)} — "
            f"Remboursements : {ariary(rembourse)} — Net : <b>{ariary(total - rembourse)}</b>",
            styles["droite"],
        )
    )
    return _construire(elements, "Rapport des ventes")


def rapport_achats(commandes, debut, fin):
    styles = _styles()
    elements = [
        _entete("RAPPORT DES ACHATS", f"du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}", styles=styles),
        Spacer(1, 6),
    ]
    donnees = [["N°", "Date", "Fournisseur", "Statut", "Total"]]
    total = 0
    for commande in commandes:
        total += commande.total
        donnees.append(
            [
                commande.numero,
                timezone.localtime(commande.date_commande).strftime("%d/%m/%Y"),
                Paragraph(escape(commande.fournisseur.nom), styles["petit"]),
                commande.get_statut_display(),
                ariary(commande.total),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [35 * mm, 28 * mm, 55 * mm, 35 * mm, 27 * mm],
            styles,
            alignements={4: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 6))
    elements.append(
        Paragraph(
            f"<b>{len(commandes)} commande(s)</b> — Montant total : {ariary(total)}",
            styles["droite"],
        )
    )
    return _construire(elements, "Rapport des achats")


def rapport_peremptions(lots, jours):
    styles = _styles()
    elements = [
        _entete(
            "PRODUITS PÉRIMÉS / PROCHES DE LA PÉREMPTION",
            f"Horizon : {jours} jours",
            styles=styles,
        ),
        Spacer(1, 6),
    ]
    donnees = [["Médicament", "Lot", "Péremption", "Jours restants", "Quantité", "État"]]
    for lot in lots:
        jours_restants = lot.jours_avant_peremption
        etat = "Périmé" if lot.est_perime else "Proche péremption"
        donnees.append(
            [
                Paragraph(escape(str(lot.medicament)), styles["petit"]),
                escape(lot.numero_lot),
                lot.date_peremption.strftime("%d/%m/%Y"),
                str(jours_restants),
                str(lot.quantite),
                etat,
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [65 * mm, 30 * mm, 27 * mm, 25 * mm, 18 * mm, 35 * mm],
            styles,
            alignements={3: "CENTER", 4: "CENTER"},
        )
    )
    return _construire(elements, "Rapport des péremptions")
