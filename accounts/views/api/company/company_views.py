from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Company
from accounts.serializers import CompanySerializer


class CompanyCreateView(generics.CreateAPIView):
    """Create a company for the authenticated user."""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a company",
        request_body=CompanySerializer,
        responses={
            201: CompanySerializer,
            400: openapi.Response(
                description="User already has a company",
                examples={
                    "application/json": {
                        "detail": "You already have a company. Each user can only have one company.",
                        "existing_company": {"id": "uuid", "name": "Example Corp"},
                    }
                },
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        """Override to check if user already has a company."""
        # Check if user already has a company
        if hasattr(request.user, "companies"):
            existing_company = request.user.companies.first()
            if existing_company:
                return Response(
                    {
                        "detail": "You already have a company. Each user can only have one company.",
                        "existing_company": {
                            "id": str(existing_company.id),
                            "name": existing_company.name,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CompanyUpdateView(generics.UpdateAPIView):
    """Update company details including capital structure fields."""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    http_method_names = ["patch", "put"]

    def get_queryset(self):
        """Only allow updating companies owned by the user."""
        return Company.objects.filter(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Update company details",
        operation_description=(
            "Update company information including capital structure fields. "
            "Supports partial updates (PATCH). Validates capital structure relationships: "
            "Authorized Capital > Issued Capital >= Paid-up Capital"
        ),
        request_body=CompanySerializer,
        responses={
            200: CompanySerializer,
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "authorized_capital_amount": [
                            "Authorized Capital must be greater than Issued Capital."
                        ]
                    }
                },
            ),
            404: openapi.Response(description="Company not found"),
        },
    )
    def patch(self, request, *args, **kwargs):
        """Handle PATCH request for partial update."""
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Handle PUT request for full update."""
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Save the updated company with updated_by tracking."""
        serializer.save(updated_by=self.request.user)
