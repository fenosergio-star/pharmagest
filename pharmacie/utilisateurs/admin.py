from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Informations pharmacie", {"fields": ("role", "telephone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations pharmacie", {"fields": ("role", "telephone")}),
    )
