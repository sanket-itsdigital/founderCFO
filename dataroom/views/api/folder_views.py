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
        # Superusers see all folders
        if self.request.user.is_superuser:
            return Folder.objects.filter(is_active=True).order_by("name")
        
        # Companies see only their selected folders
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                from dataroom.models import CompanyFolderSelection
                selected_folder_ids = CompanyFolderSelection.objects.filter(
                    company=company
                ).values_list("folder_id", flat=True)
                return Folder.objects.filter(
                    id__in=selected_folder_ids, is_active=True
                ).order_by("name")
        
        return Folder.objects.none()

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
