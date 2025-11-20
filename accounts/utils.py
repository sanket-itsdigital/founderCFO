from __future__ import annotations

from typing import Optional

from accounts.models import Company, TeamMember, User


def get_user_company(user: User) -> Optional[Company]:
    """Return the primary company associated with the given user."""
    if not user or not user.is_authenticated:
        return None

    owned_companies = getattr(user, "companies", None)
    if owned_companies and owned_companies.exists():
        return owned_companies.first()

    membership = (
        getattr(user, "team_memberships", TeamMember.objects.none())
        .filter(is_active=True)
        .select_related("company")
        .first()
    )
    if membership:
        return membership.company
    return None
