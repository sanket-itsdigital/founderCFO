from django.contrib import admin

from dataroom.models import (
    Folder,
    Document,
    DocumentVersion,
    FileCategory,
    Question,
    AccessLog,
    CompanyFolderSelection,
    CompanyCategorySelection,
)

# Register your models here.


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "created_at")
    search_fields = ("name", "description")
    list_filter = ("is_active", "created_at")
    ordering = ("name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "folder",
        "size_bytes",
        "views_count",
        "downloads_count",
        "created_at",
    )
    search_fields = ("name", "company__name", "folder__name", "access_notes")
    list_filter = ("folder", "created_at", "company")
    readonly_fields = ("views_count", "downloads_count", "size_bytes")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_no", "size_bytes", "created_at")
    search_fields = ("document__name",)
    list_filter = ("created_at",)
    readonly_fields = ("size_bytes",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "folder", "description", "is_active", "created_at")
    search_fields = ("name", "folder__name", "description")
    list_filter = ("is_active", "folder", "created_at")
    ordering = ("folder__name", "name")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "asked_by",
        "question",
        "is_answered",
        "answer_by",
        "created_at",
    )
    search_fields = ("question", "answer", "document__name", "asked_by__email")
    list_filter = ("is_answered", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "user",
        "document",
        "action",
        "ip_address",
        "timestamp",
    )
    search_fields = (
        "company__name",
        "user__email",
        "document__name",
        "ip_address",
    )
    list_filter = ("action", "timestamp", "company")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"


@admin.register(CompanyFolderSelection)
class CompanyFolderSelectionAdmin(admin.ModelAdmin):
    list_display = ("company", "folder", "selected_at")
    search_fields = ("company__name", "folder__name")
    list_filter = ("selected_at", "company", "folder")
    readonly_fields = ("selected_at",)
    ordering = ("-selected_at",)
    date_hierarchy = "selected_at"


@admin.register(CompanyCategorySelection)
class CompanyCategorySelectionAdmin(admin.ModelAdmin):
    list_display = ("company", "category", "selected_at")
    search_fields = ("company__name", "category__name")
    list_filter = ("selected_at", "company", "category")
    readonly_fields = ("selected_at",)
    ordering = ("-selected_at",)
    date_hierarchy = "selected_at"

