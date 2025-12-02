from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from dataroom.models import (
    FileCategory,
    CompanyCategorySelection,
    CompanyFolderSelection,
)
from dataroom.serializers import (
    CategorySelectionSerializer,
    CompanyCategorySelectionSerializer,
)


class AvailableCategoriesListView(generics.ListAPIView):
    """
    List available categories from folders selected by the company.
    Shows selection status for the company.
    """

    serializer_class = CategorySelectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Get company's selected folders
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                selected_folders = CompanyFolderSelection.objects.filter(
                    company=company
                ).values_list("folder_id", flat=True)

                if not selected_folders:
                    # If no folders selected, return empty queryset
                    # Could also return all categories, but for security, return empty
                    return FileCategory.objects.none()

                # Get categories from selected folders only
                return (
                    FileCategory.objects.filter(
                        folder_id__in=selected_folders, is_active=True
                    )
                    .select_related("folder")
                    .order_by("folder__name", "name")
                )

        return FileCategory.objects.none()

    def list(self, request, *args, **kwargs):
        """Override to provide helpful message if no folders selected or no categories"""
        response = super().list(request, *args, **kwargs)

        # Check if company has selected folders
        if hasattr(request.user, "companies"):
            company = request.user.companies.first()
            if company:
                selected_folders = CompanyFolderSelection.objects.filter(
                    company=company
                ).select_related("folder")
                selected_folders_count = selected_folders.count()

                if selected_folders_count == 0:
                    # Replace response data with helpful message
                    response.data = {
                        "results": [],
                        "message": "Please select folders first to view available categories.",
                        "selected_folders_count": 0,
                        "hint": "Use POST /api/dataroom/company/folders/select/ to select folders first.",
                    }
                else:
                    # Check if selected folders have categories
                    selected_folder_ids = selected_folders.values_list(
                        "folder_id", flat=True
                    )
                    total_categories = FileCategory.objects.filter(
                        folder_id__in=selected_folder_ids, is_active=True
                    ).count()

                    # Handle both paginated (dict) and non-paginated (list) responses
                    if isinstance(response.data, list):
                        results = response.data
                        if len(results) == 0:
                            response.data = {
                                "results": [],
                                "message": (
                                    "No categories available in your selected folders. Please contact admin to add categories."
                                    if total_categories == 0
                                    else "No active categories found in selected folders."
                                ),
                                "selected_folders_count": selected_folders_count,
                                "total_categories_in_folders": total_categories,
                            }
                    else:
                        # Paginated response (dict)
                        results = response.data.get("results", [])
                        if total_categories == 0:
                            response.data["message"] = (
                                "No categories available in your selected folders. Please contact admin to add categories."
                            )
                            response.data["selected_folders_count"] = (
                                selected_folders_count
                            )
                            response.data["total_categories_in_folders"] = 0
                        elif len(results) == 0:
                            response.data["message"] = (
                                "No active categories found in selected folders."
                            )
                            response.data["selected_folders_count"] = (
                                selected_folders_count
                            )
                            response.data["total_categories_in_folders"] = (
                                total_categories
                            )

        return response

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CompanyCategorySelectionView(APIView):
    """
    Select or deselect categories for the company.
    POST: Select categories (provide list of category IDs)
    DELETE: Deselect categories (provide list of category IDs)
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_company(self):
        """Get company from request user"""
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                return company
        return None

    def _validate_categories_belong_to_selected_folders(self, company, category_ids):
        """Validate that categories belong to company's selected folders"""
        selected_folders = CompanyFolderSelection.objects.filter(
            company=company
        ).values_list("folder_id", flat=True)

        categories = FileCategory.objects.filter(
            id__in=category_ids, folder_id__in=selected_folders, is_active=True
        )

        if categories.count() != len(category_ids):
            return (
                None,
                "Some category IDs are invalid or don't belong to selected folders.",
            )

        return categories, None

    def post(self, request, *args, **kwargs):
        """Select categories for company"""
        company = self._get_company()
        if not company:
            return Response(
                {"detail": "No company found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        

        category_ids = request.data.get("category_ids", [])
        if not category_ids:
            return Response(
                {"detail": "No category_ids provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(category_ids, list):
            return Response(
                {"detail": "category_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate categories belong to selected folders
        categories, error = self._validate_categories_belong_to_selected_folders(
            company, category_ids
        )
        if error:
            return Response(
                {"detail": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create selections
        created = []
        for category in categories:
            selection, created_flag = CompanyCategorySelection.objects.get_or_create(
                company=company,
                category=category,
                defaults={
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            if created_flag:
                created.append(selection.id)

        return Response(
            {
                "message": f"Selected {len(created)} category/categories.",
                "selected_count": len(created),
                "total_selected": CompanyCategorySelection.objects.filter(
                    company=company
                ).count(),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, *args, **kwargs):
        """Deselect categories for company"""
        company = self._get_company()
        if not company:
            return Response(
                {"detail": "No company found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category_ids = request.data.get("category_ids", [])
        if not isinstance(category_ids, list):
            return Response(
                {"detail": "category_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete selections
        deleted_count, _ = CompanyCategorySelection.objects.filter(
            company=company, category_id__in=category_ids
        ).delete()

        return Response(
            {
                "message": f"Deselected {deleted_count} category/categories.",
                "deselected_count": deleted_count,
                "total_selected": CompanyCategorySelection.objects.filter(
                    company=company
                ).count(),
            },
            status=status.HTTP_200_OK,
        )


class CompanySelectedCategoriesListView(generics.ListAPIView):
    """
    List categories selected by the company.
    Optional query parameter: folder_id - Filter categories by folder
    """

    serializer_class = CompanyCategorySelectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "companies"):
            company = self.request.user.companies.first()
            if company:
                queryset = (
                    CompanyCategorySelection.objects.filter(company=company)
                    .select_related("category", "category__folder")
                )
                
                # Filter by folder_id if provided in query parameters
                folder_id = self.request.query_params.get("folder_id")
                if folder_id:
                    queryset = queryset.filter(category__folder_id=folder_id)
                
                return queryset.order_by("-selected_at")
        return CompanyCategorySelection.objects.none()
