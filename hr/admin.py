from django.contrib import admin
from django.utils.html import format_html

from hr.models import (
    Department,
    Headcount,
    Role,
    Recruitment,
    Category,
    Budget,
)


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


@admin.register(Recruitment)
class RecruitmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job_title",
        "department",
        "company",
        "status",
        "positions_required",
        "applications_received",
        "offers_accepted",
        "source",
        "posting_date",
        "actual_close_date",
    )
    search_fields = (
        "job_title",
        "company__name",
        "department__name",
        "source",
    )
    list_filter = (
        "status",
        "source",
        "company",
        "department",
        "posting_date",
    )
    ordering = ("-posting_date",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "time_to_hire_days",
        "cost_per_hire",
        "conversion_rate",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "company",
                    "job_title",
                    "department",
                    "status",
                    "source",
                )
            },
        ),
        (
            "Position Details",
            {
                "fields": (
                    "positions_required",
                    "posting_date",
                    "target_close_date",
                    "actual_close_date",
                    "salary_range_min",
                    "salary_range_max",
                )
            },
        ),
        (
            "Recruitment Metrics",
            {
                "fields": (
                    "applications_received",
                    "interviews_conducted",
                    "offers_made",
                    "offers_accepted",
                    "cost_spent",
                )
            },
        ),
        (
            "Calculated Metrics",
            {
                "fields": (
                    "time_to_hire_days",
                    "cost_per_hire",
                    "conversion_rate",
                ),
                "classes": ("collapse",),
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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("created_at", "updated_at")
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "description")},
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


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "category",
        "department",
        "period",
        "budget_amount",
        "actual_amount",
        "variance_display",
        "status",
        "created_at",
    )
    search_fields = (
        "company__name",
        "category__name",
        "department__name",
        "notes",
    )
    list_filter = (
        "company",
        "category",
        "department",
        "period",
        "created_at",
    )
    ordering = ("-period", "-created_at")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "variance",
        "variance_percentage",
        "status",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "company",
                    "period",
                    "category",
                    "department",
                )
            },
        ),
        (
            "Budget Details",
            {
                "fields": (
                    "budget_amount",
                    "actual_amount",
                    "notes",
                )
            },
        ),
        (
            "Calculated Metrics",
            {
                "fields": (
                    "variance",
                    "variance_percentage",
                    "status",
                ),
                "classes": ("collapse",),
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

    def variance_display(self, obj):
        """Display variance in a formatted way"""
        variance = obj.variance
        if variance >= 0:
            formatted_value = f"+₹{variance:,.2f}"
            return format_html('<span style="color: red;">{}</span>', formatted_value)
        else:
            formatted_value = f"-₹{abs(variance):,.2f}"
            return format_html('<span style="color: green;">{}</span>', formatted_value)

    variance_display.short_description = "Variance"
    variance_display.admin_order_field = "variance"
