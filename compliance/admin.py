from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from compliance.forms import ComplianceTaskImportForm
from compliance.models import ComplianceTaskMaster, CompliancePayments
from compliance.services.import_tasks import (
    ALLOWED_ROW_NUMBERS,
    SHEET_NAME,
    TaskImportError,
    import_compliance_tasks_from_excel,
)

# Register your models here.


@admin.register(ComplianceTaskMaster)
class ComplianceTaskMasterAdmin(admin.ModelAdmin):
    change_list_template = "admin/compliance/compliancetaskmaster/change_list.html"
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="compliance_compliancetaskmaster_import_excel",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        allowed_rows_display = [str(number) for number in sorted(ALLOWED_ROW_NUMBERS)]
        extra_context.update(
            {
                "import_excel_url": reverse(
                    "admin:compliance_compliancetaskmaster_import_excel"
                ),
                "can_import_tasks": request.user.is_superuser,
                "allowed_rows": allowed_rows_display,
                "sheet_name": SHEET_NAME,
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def import_excel_view(self, request):
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can import master compliance tasks.",
                level=messages.ERROR,
            )
            return redirect(self._get_changelist_url())

        if request.method == "POST":
            form = ComplianceTaskImportForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = form.cleaned_data["excel_file"]
                try:
                    result = import_compliance_tasks_from_excel(
                        uploaded_file, request.user
                    )
                except TaskImportError as exc:
                    self.message_user(request, str(exc), level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        (
                            f"Imported {result.created} new task(s) "
                            f"and updated {result.updated} existing task(s)."
                        ),
                        level=messages.SUCCESS,
                    )
                    if result.skipped:
                        skipped_messages = "; ".join(
                            [f"Row {row}: {reason}" for row, reason in result.skipped]
                        )
                        self.message_user(
                            request,
                            f"Skipped rows ({len(result.skipped)}): {skipped_messages}",
                            level=messages.WARNING,
                        )
                    return redirect(self._get_changelist_url())
        else:
            form = ComplianceTaskImportForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Import Compliance Tasks",
            "sheet_name": SHEET_NAME,
            "allowed_rows": [str(number) for number in sorted(ALLOWED_ROW_NUMBERS)],
            "changelist_url": self._get_changelist_url(),
        }
        return render(
            request, "admin/compliance/compliancetaskmaster/import_excel.html", context
        )

    def _get_changelist_url(self):
        return reverse("admin:compliance_compliancetaskmaster_changelist")

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
