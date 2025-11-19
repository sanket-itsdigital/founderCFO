from rest_framework.permissions import BasePermission

from backend.enums import UserRoleChoices


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

