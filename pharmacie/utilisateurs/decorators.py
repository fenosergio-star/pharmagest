from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN = "ADMIN"
PHARMACIEN = "PHARMACIEN"
GESTIONNAIRE = "GESTIONNAIRE"
CAISSIER = "CAISSIER"
RESPONSABLE = "RESPONSABLE"


def role_required(*roles):
    """Restreint une vue aux rôles indiqués (l'administrateur passe toujours)."""

    def decorateur(vue):
        @login_required
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if request.user.est_administrateur or request.user.role in roles:
                return vue(request, *args, **kwargs)
            raise PermissionDenied(
                "Vous n'avez pas les droits nécessaires pour accéder à cette page."
            )

        return enveloppe

    return decorateur
