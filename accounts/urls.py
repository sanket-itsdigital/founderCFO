from django.urls import path

from accounts.views.api.auth.auth_views import LogoutAPIView, SigninView
from accounts.views.api.auth.registration_views import SignupView
from accounts.views.api.company.company_views import CompanyCreateView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="api-signup"),
    path("signin/", SigninView.as_view(), name="api-signin"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    # Company registration
    path("company/register/", CompanyCreateView.as_view(), name="company-register"),
]
