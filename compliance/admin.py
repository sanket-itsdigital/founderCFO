from django.contrib import admin

from compliance.models import ComplianceTaskMaster, CompliancePayments

# Register your models here.


@admin.register(ComplianceTaskMaster)
class ComplianceTaskMasterAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "act",
        "particulars",
        "due_date",
        "next_due_date",
        "frequency",
        "status",
        "is_overdue",
        "is_admin_created",
        "company_type",
        "assignee",
    )
    search_fields = ("task_id", "act", "particulars", "assignee")
    list_filter = (
        "act",
        "status",
        "is_overdue",
        "company_type",
        "frequency",
        "is_admin_created",
        "companies",
    )
    readonly_fields = ("days_until_due", "is_overdue")
    ordering = ("-created_at",)
    date_hierarchy = "due_date"

    fieldsets = (
        (
            "Task Details",
            {
                "fields": (
                    "task_id",
                    "act",
                    "particulars",
                    "severity",
                    "frequency",
                    "company_type",
                    "assignee",
                    "is_admin_created",
                    "companies",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "due_date",
                    "next_due_date",
                    "last_filed_date",
                    "completed_date",
                    "reminder_days",
                    "days_until_due",
                    "is_overdue",
                )
            },
        ),
        (
            "Status & Evidence",
            {"fields": ("status", "evidence_url", "notes")},
        ),
        (
            "Financials",
            {
                "fields": (
                    "penalty_amount",
                    "penalty",
                    "late_fee",
                    "interest_percentage",
                    "interest_amount",
                    "payment_amount",
                    "payment_reference",
                    "consequences",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(["task_id", "is_admin_created"])
        return tuple(readonly)

    def save_model(self, request, obj, form, change):
        """Preserve admin-created flag unless a superuser explicitly changes it."""
        if not change or not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user

        if not change:
            # Only stamp admin-created status when the task is first created.
            obj.is_admin_created = request.user.is_superuser
        elif not request.user.is_superuser and obj.pk:
            # Non-superusers editing an existing record should never flip this flag.
            original_flag = (
                ComplianceTaskMaster.objects.filter(pk=obj.pk)
                .values_list("is_admin_created", flat=True)
                .first()
            )
            if original_flag is not None:
                obj.is_admin_created = original_flag

        super().save_model(request, obj, form, change)


@admin.register(CompliancePayments)
class CompliancePaymentsAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "compliance_task",
        "task_id",
        "payment_type",
        "payment_date",
        "amount",
        "is_late",
        "related_act",
    )
    search_fields = ("payment_id", "task_id", "payment_type", "reference_number")
    list_filter = ("payment_type", "is_late", "related_act", "payment_date")
    readonly_fields = ("payment_id", "days_early_or_late", "is_late")
    ordering = ("-payment_date",)
    date_hierarchy = "payment_date"
