from django.contrib import admin

from .models import JournalAudit


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("date", "utilisateur", "action", "modele", "objet_id", "adresse_ip")
    list_filter = ("modele", "date")
    search_fields = ("action", "details", "utilisateur__username")
    readonly_fields = (
        "utilisateur",
        "action",
        "modele",
        "objet_id",
        "details",
        "adresse_ip",
        "date",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
