from rest_framework import serializers
from dataroom.models import (
    Folder,
    FileCategory,
    CompanyFolderSelection,
    CompanyCategorySelection,
)


class FolderSelectionSerializer(serializers.ModelSerializer):
    """Serializer for folders with selection status for company"""

    is_selected = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "is_selected",
            "created_at",
        ]
        read_only_fields = ["id", "is_selected", "created_at"]

    def get_is_selected(self, obj):
        """Check if folder is selected by company"""
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            return False

        company = self._get_company(request)
        if not company:
            return False

        return CompanyFolderSelection.objects.filter(
            company=company, folder=obj
        ).exists()

    def _get_company(self, request):
        """Get company from request user"""
        if hasattr(request.user, "companies"):
            return request.user.companies.first()
        return None


class CategorySelectionSerializer(serializers.ModelSerializer):
    """Serializer for categories with selection status for company"""

    folder_name = serializers.CharField(source="folder.name", read_only=True)
    folder_id = serializers.UUIDField(source="folder.id", read_only=True)
    is_selected = serializers.SerializerMethodField()

    class Meta:
        model = FileCategory
        fields = [
            "id",
            "folder_id",
            "folder_name",
            "name",
            "description",
            "is_active",
            "is_selected",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "folder_id",
            "folder_name",
            "is_selected",
            "created_at",
        ]

    def get_is_selected(self, obj):
        """Check if category is selected by company"""
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            return False

        company = self._get_company(request)
        if not company:
            return False

        return CompanyCategorySelection.objects.filter(
            company=company, category=obj
        ).exists()

    def _get_company(self, request):
        """Get company from request user"""
        if hasattr(request.user, "companies"):
            return request.user.companies.first()
        return None


class CompanyFolderSelectionSerializer(serializers.ModelSerializer):
    """Serializer for company folder selection"""

    folder_name = serializers.CharField(source="folder.name", read_only=True)
    folder_description = serializers.CharField(
        source="folder.description", read_only=True
    )

    class Meta:
        model = CompanyFolderSelection
        fields = [
            "id",
            "folder",
            "folder_name",
            "folder_description",
            "selected_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "folder_name",
            "folder_description",
            "selected_at",
            "created_at",
        ]


class CompanyCategorySelectionSerializer(serializers.ModelSerializer):
    """Serializer for company category selection"""

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_description = serializers.CharField(
        source="category.description", read_only=True
    )
    folder_name = serializers.CharField(source="category.folder.name", read_only=True)
    folder_id = serializers.UUIDField(source="category.folder.id", read_only=True)

    class Meta:
        model = CompanyCategorySelection
        fields = [
            "id",
            "category",
            "category_name",
            "category_description",
            "folder_id",
            "folder_name",
            "selected_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "category_description",
            "folder_id",
            "folder_name",
            "selected_at",
            "created_at",
        ]
