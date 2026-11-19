from django.contrib import admin

from .models import Fournisseur


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "contact_principal", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone", "email", "numero_fiscal")
