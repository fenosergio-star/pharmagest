from django.contrib import admin

from .models import CommandeAchat, LigneAchat, LigneReception, ReceptionAchat


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "fournisseur", "date_commande", "statut", "total")
    list_filter = ("statut", "fournisseur")
    search_fields = ("numero", "fournisseur__nom")
    inlines = [LigneAchatInline]
    readonly_fields = ("numero", "date_commande")


class LigneReceptionInline(admin.TabularInline):
    model = LigneReception
    extra = 0
    readonly_fields = ("lot",)


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "commande", "date_reception", "utilisateur")
    search_fields = ("numero", "commande__numero")
    inlines = [LigneReceptionInline]
    readonly_fields = ("numero", "date_reception")


@admin.register(LigneAchat)
class LigneAchatAdmin(admin.ModelAdmin):
    list_display = ("commande", "medicament", "quantite", "quantite_recue", "prix_achat")
    search_fields = ("commande__numero", "medicament__nom")
