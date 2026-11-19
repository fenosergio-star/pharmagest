"""URLconf principale de PharmaGest."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("rapports.urls")),
    path(
        "comptes/connexion/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "comptes/deconnexion/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("comptes/", include("utilisateurs.urls")),
    path("medicaments/", include("medicaments.urls")),
    path("fournisseurs/", include("fournisseurs.urls")),
    path("clients/", include("clients.urls")),
    path("stock/", include("stock.urls")),
    path("achats/", include("achats.urls")),
    path("ventes/", include("ventes.urls")),
    path(
        "comptes/mot-de-passe/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url="/comptes/mot-de-passe/fait/",
        ),
        name="password_change",
    ),
    path(
        "comptes/mot-de-passe/fait/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
