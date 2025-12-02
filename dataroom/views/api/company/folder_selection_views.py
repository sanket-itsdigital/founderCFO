from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from dataroom.models import Folder, CompanyFolderSelection
from dataroom.serializers import (
    FolderSelectionSerializer,
    CompanyFolderSelectionSerializer,
)


class AvailableFoldersListView(generics.ListAPIView):
    """
    List all available folders (created by super admin).
    Shows selection status for the company.
    """

    serializer_class = FolderSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Folder.objects.filter(is_active=True).order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CompanyFolderSelectionView(APIView):
    """
    Select or deselect folders for the company.
    POST: Select folders (provide list of folder IDs)
    DELETE: Deselect folders (provide list of folder IDs)
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_company(self):
        """Get company from request user"""
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                return company
        return None

    def post(self, request, *args, **kwargs):
        """Select folders for company"""
        company = self._get_company()
        if not company:
            return Response(
                {"detail": "No company found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        folder_ids = request.data.get("folder_ids", [])
        if not folder_ids:
            return Response(
                {"detail": "No folder_ids provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(folder_ids, list):
            return Response(
                {"detail": "folder_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate folder IDs exist
        folders = Folder.objects.filter(id__in=folder_ids, is_active=True)
        if folders.count() != len(folder_ids):
            return Response(
                {"detail": "Some folder IDs are invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create selections
        created = []
        for folder in folders:
            selection, created_flag = CompanyFolderSelection.objects.get_or_create(
                company=company,
                folder=folder,
                defaults={
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            if created_flag:
                created.append(selection.id)

        return Response(
            {
                "message": f"Selected {len(created)} folder(s).",
                "selected_count": len(created),
                "total_selected": CompanyFolderSelection.objects.filter(
                    company=company
                ).count(),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, *args, **kwargs):
        """Deselect folders for company"""
        company = self._get_company()
        if not company:
            return Response(
                {"detail": "No company found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        folder_ids = request.data.get("folder_ids", [])
        if not isinstance(folder_ids, list):
            return Response(
                {"detail": "folder_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete selections
        deleted_count, _ = CompanyFolderSelection.objects.filter(
            company=company, folder_id__in=folder_ids
        ).delete()

        return Response(
            {
                "message": f"Deselected {deleted_count} folder(s).",
                "deselected_count": deleted_count,
                "total_selected": CompanyFolderSelection.objects.filter(
                    company=company
                ).count(),
            },
            status=status.HTTP_200_OK,
        )


class CompanySelectedFoldersListView(generics.ListAPIView):
    """
    List folders selected by the company.
    """

    serializer_class = CompanyFolderSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                return (
                    CompanyFolderSelection.objects.filter(company=company)
                    .select_related("folder")
                    .order_by("-selected_at")
                )
        return CompanyFolderSelection.objects.none()
