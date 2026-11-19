from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def ariary(valeur):
    try:
        montant = Decimal(valeur)
    except (InvalidOperation, TypeError, ValueError):
        return "0,00 Ar"
    texte = f"{montant:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte} Ar"


@register.filter
def form_control(champ):
    widget = champ.field.widget
    classe = widget.__class__.__name__
    if classe in ("CheckboxInput",):
        css = "form-check-input"
    elif "Select" in classe:
        css = "form-select"
    elif classe in ("Textarea",):
        css = "form-control"
    else:
        css = "form-control"
    widget.attrs["class"] = (widget.attrs.get("class", "") + " " + css).strip()
    return champ


@register.filter
def badge_stock(medicament):
    if medicament.stock_disponible == 0:
        return "bg-danger"
    if medicament.est_stock_faible:
        return "bg-warning text-dark"
    return "bg-success"


@register.filter
def sens_mouvement(quantite):
    try:
        return "text-success" if int(quantite) >= 0 else "text-danger"
    except (TypeError, ValueError):
        return ""
