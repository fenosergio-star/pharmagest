"""Sauvegarde simple de la base SQLite de développement."""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copie la base SQLite dans le dossier backups/ avec un horodatage."

    def handle(self, *args, **options):
        base = settings.DATABASES["default"]
        if "sqlite" not in base["ENGINE"]:
            raise CommandError(
                "Cette commande ne gère que SQLite. Utilisez pg_dump pour PostgreSQL."
            )
        source = Path(base["NAME"])
        if not source.exists():
            raise CommandError(f"Base introuvable : {source}")
        dossier = Path(settings.BASE_DIR) / "backups"
        dossier.mkdir(exist_ok=True)
        destination = dossier / f"pharmagest-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        shutil.copy2(source, destination)
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {destination}"))
