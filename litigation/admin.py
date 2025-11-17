from django.contrib import admin

from litigation.models import Case

# Register your models here.


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_number",
        "company",
        "type",
        "status",
        "risk",
        "total_exposure",
        "issue_date",
        "due_date",
    )
    search_fields = ("case_number", "company__name", "synopsis")
    list_filter = ("type", "status", "risk", "issue_date", "company")
    readonly_fields = ("total_exposure",)
    ordering = ("-created_at",)
    date_hierarchy = "issue_date"

