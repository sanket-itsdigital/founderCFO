from django.utils import timezone
from rest_framework.permissions import BasePermission

from accounts.utils import get_user_company
from backend.enums import UserRoleChoices
from subscriptions.models import CompanySubscription


class IsFounder(BasePermission):
    """Allows access only to authenticated founders (or superusers)."""

    message = "Only founders can perform this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role == UserRoleChoices.FOUNDER


class HasActiveSubscription(BasePermission):
    """Ensures the user's company has an active subscription."""

    message = "An active subscription is required to perform this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        company = getattr(request, "company", None) or get_user_company(user)
        if not company:
            return False

        today = timezone.now().date()
        return CompanySubscription.objects.filter(
            company=company,
            status=CompanySubscription.Status.ACTIVE,
            end_date__gte=today,
        ).exists()

