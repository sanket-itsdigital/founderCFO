from django.contrib import admin
from django.utils.html import format_html

from hr.models import Department, Headcount, Role


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company", "is_active", "created_at", "updated_at")
    search_fields = ("name", "company__name", "description")
    list_filter = ("is_active", "company", "created_at", "updated_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "name", "description", "is_active")},
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company", "is_active", "created_at", "updated_at")
    search_fields = ("name", "company__name", "description")
    list_filter = ("is_active", "company", "created_at", "updated_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "name", "description", "is_active")},
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Headcount)
class HeadcountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "company",
        "department",
        "role",
        "level",
        "status",
        "employment",
        "location",
        "salary_display",
        "start_date",
        "end_date",
    )
    search_fields = (
        "name",
        "email",
        "company__name",
        "department__name",
        "role__name",
        "location",
    )
    list_filter = (
        "status",
        "employment",
        "gender",
        "level",
        "company",
        "department",
        "role",
        "start_date",
        "end_date",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "company",
                    "name",
                    "email",
                    "department",
                    "role",
                    "level",
                )
            },
        ),
        (
            "Employment Details",
            {
                "fields": (
                    "status",
                    "employment",
                    "gender",
                    "location",
                    "start_date",
                    "end_date",
                    "exit_reason",
                )
            },
        ),
        (
            "Compensation",
            {
                "fields": (
                    "salary_annual",
                    "benefits_annual",
                    "bouns_percent",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def salary_display(self, obj):
        """Display salary in a formatted way"""
        if obj.salary_annual:
            return f"₹{obj.salary_annual:,.2f}"
        return "-"

    salary_display.short_description = "Annual Salary"
    salary_display.admin_order_field = "salary_annual"
