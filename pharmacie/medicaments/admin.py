from django.contrib import admin

from .models import Categorie, Medicament


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_creation")
    search_fields = ("nom",)


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "categorie",
        "forme",
        "dosage",
        "prix_vente",
        "stock_total",
        "statut",
    )
    list_filter = ("categorie", "forme", "statut")
    search_fields = ("nom", "denomination_generique", "code_barres", "laboratoire")
    readonly_fields = ("date_creation",)
