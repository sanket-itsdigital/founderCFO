"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from functools import wraps
from django.contrib.auth.models import AnonymousUser

from backend.views import dashboard
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions


def bypass_auth(view_func):
    """Decorator to bypass authentication for Swagger views."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Set user as anonymous to bypass authentication checks
        request.user = AnonymousUser()
        return view_func(request, *args, **kwargs)

    return wrapper


schema_view = get_schema_view(
    openapi.Info(
        title="FounderCFO",
        default_version="v1",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=(),  # No authentication required for Swagger
)

# Wrap Swagger views to bypass authentication
swagger_ui_view = bypass_auth(schema_view.with_ui("swagger", cache_timeout=0))
redoc_ui_view = bypass_auth(schema_view.with_ui("redoc", cache_timeout=0))
swagger_json_view = bypass_auth(schema_view.without_ui(cache_timeout=0))

urlpatterns = [
    # Swagger URLs - using wrapped views that bypass authentication
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        swagger_json_view,
        name="schema-json",
    ),
    path(
        "swagger/",
        swagger_ui_view,
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        redoc_ui_view,
        name="schema-redoc",
    ),
    path("", dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("api/account/", include("accounts.urls")),
    path("api/litigation/", include("litigation.urls", namespace="litigation")),
    path("api/dataroom/", include("dataroom.urls", namespace="dataroom")),
    path("api/compliance/", include("compliance.urls", namespace="compliance")),
    path("api/captable/", include("captable.urls", namespace="captable")),
    path(
        "api/subscriptions/",
        include("subscriptions.urls", namespace="subscriptions"),
    ),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
