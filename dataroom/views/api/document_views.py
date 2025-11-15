from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from dataroom.models import Document, DocumentVersion, Folder, AccessLog
from dataroom.serializers import (
    DocumentSerializer,
    DocumentCreateSerializer,
    DocumentVersionSerializer,
    VersionCompareSerializer,
)
from dataroom.utils import log_api_access


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentCreateSerializer
        return DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.all()
        company_id = self.request.query_params.get("company_id")
        folder_id = self.request.query_params.get("folder_id")
        search = self.request.query_params.get("search")

        # If company_id is provided, filter by company
        if company_id:
            qs = qs.filter(company_id=company_id)

            # For non-superusers, only show documents from selected folders
            if not self.request.user.is_superuser:
                from dataroom.models import (
                    CompanyFolderSelection,
                    CompanyCategorySelection,
                )

                # Get selected folders for this company
                selected_folders = CompanyFolderSelection.objects.filter(
                    company_id=company_id
                ).values_list("folder_id", flat=True)

                # Get selected categories for this company
                selected_categories = CompanyCategorySelection.objects.filter(
                    company_id=company_id
                ).values_list("category_id", flat=True)

                # Filter documents by selected folders
                qs = qs.filter(folder_id__in=selected_folders)

                # Optionally filter by selected categories if category field exists
                # Note: Document model doesn't have category field, so this is for future use

        if folder_id:
            qs = qs.filter(folder_id=folder_id)

            # For non-superusers, verify folder is selected by company
            if not self.request.user.is_superuser and company_id:
                from dataroom.models import CompanyFolderSelection

                is_selected = CompanyFolderSelection.objects.filter(
                    company_id=company_id, folder_id=folder_id
                ).exists()
                if not is_selected:
                    return qs.none()

        if search:
            qs = qs.filter(name__icontains=search)
        return qs.select_related("folder")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class DocumentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Document.objects.all().select_related("folder")
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to log document view"""
        response = super().retrieve(request, *args, **kwargs)
        # Log document view access
        document = self.get_object()
        log_api_access(
            request=request,
            action=AccessLog.VIEW,
            document=document,
        )
        # Increment views count
        document.views_count += 1
        document.save(update_fields=["views_count", "updated_at"])
        return response


class DocumentDownloadView(generics.RetrieveAPIView):
    """
    Download a document file.
    Logs the download action in AccessLog.
    """

    queryset = Document.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """Download document and log access"""
        document = self.get_object()

        # Log document download access
        log_api_access(
            request=request,
            action=AccessLog.DOWNLOAD,
            document=document,
        )

        # Increment downloads count
        document.downloads_count += 1
        document.save(update_fields=["downloads_count", "updated_at"])

        # Return file response
        if document.file:
            try:
                file_handle = document.file.open("rb")
                response = FileResponse(
                    file_handle, content_type="application/octet-stream"
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="{document.name}"'
                )
                return response
            except Exception as e:
                return Response({"detail": f"Error opening file: {str(e)}"}, status=500)
        else:
            return Response({"detail": "Document file not found."}, status=404)


class FolderDocumentsView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        folder_id = self.kwargs["folder_id"]
        return Document.objects.filter(folder_id=folder_id).select_related("folder")


class DocumentVersionListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        document_id = self.request.query_params.get("document_id")
        return DocumentVersion.objects.filter(document_id=document_id)

    def perform_create(self, serializer):
        document_id = self.request.data.get("document")
        if not document_id:
            return super().perform_create(serializer)
        # next version number
        try:
            last = (
                DocumentVersion.objects.filter(document_id=document_id)
                .order_by("-version_no")
                .first()
            )
            next_no = (last.version_no + 1) if last else 1
        except Exception:
            next_no = 1
        instance = serializer.save(
            version_no=next_no,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        # update document latest file/size
        doc = instance.document
        doc.file = instance.file
        doc.size_bytes = instance.size_bytes
        doc.save(update_fields=["file", "size_bytes", "updated_at", "updated_by"])


class VersionCompareView(generics.GenericAPIView):
    serializer_class = VersionCompareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_id = serializer.validated_data["old_version_id"]
        new_id = serializer.validated_data["new_version_id"]
        try:
            old_v = DocumentVersion.objects.get(id=old_id)
            new_v = DocumentVersion.objects.get(id=new_id)
        except DocumentVersion.DoesNotExist:
            return Response({"detail": "Version not found"}, status=404)
        # Basic metadata compare; real diffing for PDFs/docs is non-trivial.
        result = {
            "document": str(old_v.document_id),
            "old": {
                "version_no": old_v.version_no,
                "size_bytes": old_v.size_bytes,
                "created_at": old_v.created_at,
            },
            "new": {
                "version_no": new_v.version_no,
                "size_bytes": new_v.size_bytes,
                "created_at": new_v.created_at,
            },
            "changed_size_bytes": (new_v.size_bytes or 0) - (old_v.size_bytes or 0),
        }
        return Response(result)
