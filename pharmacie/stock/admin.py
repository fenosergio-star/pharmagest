from django.contrib import admin

from .models import LotStock, MouvementStock


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = (
        "medicament",
        "numero_lot",
        "date_peremption",
        "quantite",
        "bloque",
    )
    list_filter = ("bloque", "date_peremption")
    search_fields = ("medicament__nom", "numero_lot")


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ("date", "medicament", "lot", "type", "quantite", "utilisateur")
    list_filter = ("type", "date")
    search_fields = ("medicament__nom", "lot__numero_lot", "reference", "motif")
    readonly_fields = ("date",)
