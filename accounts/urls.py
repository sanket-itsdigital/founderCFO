from django.urls import path

from accounts.views.api.auth.auth_views import (
    ChangePasswordAPIView,
    LogoutAPIView,
    ProfileAPIView,
    SigninView,
)
from accounts.views.api.auth.registration_views import SignupView
from accounts.views.api.company.company_views import (
    CompanyCreateView,
    CompanyUpdateView,
)
from accounts.views.api.company.team_views import (
    TeamMemberDetailView,
    TeamMemberListCreateView,
)
from accounts.views.api.user_info import UserInfoAPIView
from captable.views.api import CompanyInfoView
from dataroom.admin_views import login_admin, logout_page, user_profile, list_users, list_company_subscriptions

urlpatterns = [
    path("login-admin/", login_admin, name="login_admin"),
    path("admin-logout/", logout_page, name="admin_logout"),
    path("admin-user-profile/", user_profile, name="admin_user_profile"),
    path("list-users/", list_users, name="list_users"),
    path("list-subscriptions/", list_company_subscriptions, name="list_subscriptions"),
    path("signup/", SignupView.as_view(), name="api-signup"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    path("signin/", SigninView.as_view(), name="api-signin"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("profile/", ProfileAPIView.as_view(), name="api-profile"),
    # Company registration
    path("company/register/", CompanyCreateView.as_view(), name="company-register"),
    path("company/<uuid:id>/", CompanyUpdateView.as_view(), name="company-update"),
    path(
        "company/team-members/",
        TeamMemberListCreateView.as_view(),
        name="team-member-list",
    ),
    path(
        "company/team-members/<uuid:pk>/",
        TeamMemberDetailView.as_view(),
        name="team-member-detail",
    ),
    path("user-info/", UserInfoAPIView.as_view(), name="user-info"),
    path("company/", CompanyInfoView.as_view(), name="company-info"),
]
