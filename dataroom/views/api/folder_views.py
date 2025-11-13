from rest_framework import generics, permissions
from dataroom.models import Folder
from dataroom.serializers import FolderSerializer


class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class FolderListCreateView(generics.ListCreateAPIView):
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_id = self.request.query_params.get("company_id")
        return Folder.objects.filter(company_id=company_id)

    def perform_create(self, serializer):
        # allow only superusers to create folders
        if not self.request.user.is_superuser:
            self.permission_denied(
                self.request, message="Only admin can create folders"
            )
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class FolderRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]
