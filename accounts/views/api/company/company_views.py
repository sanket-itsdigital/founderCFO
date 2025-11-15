from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.serializers import CompanySerializer


class CompanyCreateView(generics.CreateAPIView):
    """Create a company for the authenticated user."""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

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
