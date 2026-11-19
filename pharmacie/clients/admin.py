from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "actif", "date_creation")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone", "email")
