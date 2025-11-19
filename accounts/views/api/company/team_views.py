from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from accounts.models import TeamMember
from accounts.permissions import IsFounder
from accounts.serializers.team import (
    TeamMemberCreateSerializer,
    TeamMemberSerializer,
    TeamMemberUpdateSerializer,
)


class CompanyTeamMixin:
    """Helpers for getting the current founder's company context."""

    def _get_company(self):
        company_manager = getattr(self.request.user, "companies", None)
        if company_manager is None:
            raise ValidationError("You do not have a company yet.")
        company = company_manager.first()
        if company is None:
            raise ValidationError("You must create a company before managing a team.")
        return company

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self._get_company()
        return context


class TeamMemberListCreateView(CompanyTeamMixin, generics.ListCreateAPIView):
    """List and create company team members."""

    permission_classes = [IsAuthenticated, IsFounder]

    def get_queryset(self):
        return (
            TeamMember.objects.filter(company=self._get_company())
            .select_related("user", "invited_by", "company")
            .order_by("user__first_name", "user__last_name")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TeamMemberCreateSerializer
        return TeamMemberSerializer


class TeamMemberDetailView(CompanyTeamMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or remove a team member."""

    permission_classes = [IsAuthenticated, IsFounder]
    lookup_field = "pk"

    def get_queryset(self):
        return (
            TeamMember.objects.filter(company=self._get_company())
            .select_related("user", "invited_by", "company")
            .order_by("user__first_name", "user__last_name")
        )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return TeamMemberUpdateSerializer
        return TeamMemberSerializer
