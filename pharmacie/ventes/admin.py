from django.contrib import admin

from .models import LigneVente, Paiement, RetourVente, Vente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ("numero", "date_vente", "client", "utilisateur", "mode_paiement", "statut")
    list_filter = ("statut", "mode_paiement", "date_vente")
    search_fields = ("numero", "client__nom")
    inlines = [LigneVenteInline, PaiementInline]
    readonly_fields = ("numero", "date_vente")


@admin.register(RetourVente)
class RetourVenteAdmin(admin.ModelAdmin):
    list_display = ("vente", "ligne_vente", "quantite", "montant_rembourse", "remise_en_stock", "date")
    list_filter = ("remise_en_stock", "date")
    search_fields = ("vente__numero", "ligne_vente__medicament__nom")


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("vente", "montant", "mode", "statut", "date")
    list_filter = ("mode", "statut")
