from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.serializers import CompanySerializer


class CompanyCreateView(generics.CreateAPIView):
    """Create a company for the authenticated user."""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """Override to return a friendly message on success."""
        return super().create(request, *args, **kwargs)
