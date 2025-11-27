from __future__ import annotations

from threading import local
from typing import Callable, Iterable

from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser

from accounts.utils import get_user_company
from backend.enums import UserRoleChoices


class RequestContext:
    """Thread-local like storage for request-scoped data."""

    _state = local()


def set_current_company(company):
    RequestContext._state.company = company


def get_current_company():
    return getattr(RequestContext._state, "company", None)


class SwaggerAuthBypassMiddleware:
    """Bypass authentication for Swagger/Redoc endpoints by setting user as anonymous.

    This middleware runs before AuthenticationMiddleware to prevent authentication,
    and the user is set again after AuthenticationMiddleware in CompanyScopeMiddleware.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # Check if this is a Swagger or Redoc path
        if (
            path.startswith("/swagger")
            or path.startswith("/redoc")
            or path.startswith("/swagger/")
            or path.startswith("/redoc/")
        ):
            # Set user as anonymous to bypass authentication checks
            request.user = AnonymousUser()
            # Mark request to skip authentication
            request._swagger_bypass = True
        return self.get_response(request)


class CompanyScopeMiddleware:
    """Attach the active company to the request and shared context."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # If this is a Swagger path, ensure user remains anonymous after AuthenticationMiddleware
        if getattr(request, "_swagger_bypass", False):
            request.user = AnonymousUser()

        set_current_company(None)
        request.company = None
        if hasattr(request, "user") and request.user.is_authenticated:
            company = get_user_company(request.user)
            request.company = company
            set_current_company(company)
        response = self.get_response(request)
        set_current_company(None)
        return response


class RoleAccessMiddleware:
    """Enforce high-level role capabilities across API endpoints."""

    SAFE_METHODS: Iterable[str] = ("GET", "HEAD", "OPTIONS")
    INVESTOR_ALLOWED_PREFIXES = getattr(
        settings,
        "INVESTOR_ALLOWED_PREFIXES",
        ("/api/dataroom/", "/api/captable/", "/api/esop/"),
    )
    ACCOUNT_ENDPOINTS = getattr(
        settings,
        "ACCOUNT_ENDPOINTS_ALLOWED",
        (
            "/api/account/signin/",
            "/api/account/signup/",
            "/api/account/logout/",
            "/api/account/profile/",
            "/api/account/user-info/",
        ),
    )

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for Swagger/Redoc endpoints
        path = request.path
        if (
            path.startswith("/swagger/")
            or path.startswith("/redoc/")
            or path.startswith("/swagger")
            or path.startswith("/redoc")
        ):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_superuser:
            role = getattr(user, "role", None)
            method = request.method.upper()

            if path.startswith("/api/"):
                if role == UserRoleChoices.CFO and method not in self.SAFE_METHODS:
                    return self._deny("CFOs have read-only access.")

                if role == UserRoleChoices.INVESTOR:
                    if not self._is_investor_allowed(path):
                        return self._deny(
                            "Investors can only access Dataroom, ESOP, and CapTable modules."
                        )

                if role == UserRoleChoices.ACCOUNTANT:
                    # Accountants have edit permissions but must respect subscription status.
                    pass

        return self.get_response(request)

    def _is_investor_allowed(self, path: str) -> bool:
        if any(path.startswith(endpoint) for endpoint in self.ACCOUNT_ENDPOINTS):
            return True
        return any(path.startswith(prefix) for prefix in self.INVESTOR_ALLOWED_PREFIXES)

    @staticmethod
    def _deny(message: str):
        return JsonResponse({"detail": message}, status=403)
