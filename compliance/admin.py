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
        "status",
        "is_overdue",
        "company_type",
        "assignee",
    )
    search_fields = ("task_id", "act", "particulars", "assignee")
    list_filter = ("act", "status", "is_overdue", "company_type", "frequency")
    readonly_fields = ("task_id", "days_until_due", "is_overdue")
    ordering = ("-created_at",)
    date_hierarchy = "due_date"


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
