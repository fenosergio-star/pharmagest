from django.conf import settings


def pharmacie(request):
    return {
        "PHARMACIE_NOM": settings.PHARMACIE_NOM,
        "PHARMACIE_ADRESSE": settings.PHARMACIE_ADRESSE,
        "PHARMACIE_TELEPHONE": settings.PHARMACIE_TELEPHONE,
        "PHARMACIE_EMAIL": settings.PHARMACIE_EMAIL,
        "PHARMACIE_NIF": settings.PHARMACIE_NIF,
        "PHARMACIE_STAT": settings.PHARMACIE_STAT,
        "JOURS_ALERTE_PEREMPTION": settings.JOURS_ALERTE_PEREMPTION,
    }
