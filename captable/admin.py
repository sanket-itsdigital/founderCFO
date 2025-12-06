from django.contrib import admin

from captable.models import (
    CapTableEventDocument,
    CapTableEvents,
    CapitalizationTable,
    ESOPGrant,
    Shareholder,
    VestingSchedule,
)


@admin.register(CapTableEvents)
class CapTableEventsAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "company",
        "event_type",
        "date",
        "valuation",
        "amount_raised",
    )
    list_filter = ("event_type", "company")
    search_fields = ("event_name", "description", "company__name")
    ordering = ("-date",)


@admin.register(Shareholder)
class ShareholderAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "investor_type", "email", "kyc_verified")
    list_filter = ("investor_type", "kyc_verified", "company")
    search_fields = ("name", "email", "company__name")


@admin.register(CapTableEventDocument)
class CapTableEventDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "created_at")
    list_filter = ("event",)
    search_fields = ("name", "event__event_name")


@admin.register(CapitalizationTable)
class CapitalizationTableAdmin(admin.ModelAdmin):
    list_display = (
        "share_class_name",
        "company",
        "event",
        "shareholder",
        "share_class_type",
        "shares_issued",
        "price_per_share",
        "amount",
    )
    list_filter = ("share_class_type", "company")
    search_fields = ("share_class_name", "shareholder__name", "company__name")


@admin.register(VestingSchedule)
class VestingScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "total_shares",
        "start_date",
        "vesting_frequency",
        "cliff_period_months",
        "total_vesting_period_months",
        "single_trigger",
        "double_trigger",
    )
    list_filter = ("vesting_frequency", "single_trigger", "double_trigger", "company")
    search_fields = ("name", "company__name")
    ordering = ("name",)


@admin.register(ESOPGrant)
class ESOPGrantAdmin(admin.ModelAdmin):
    list_display = (
        "employee_name",
        "employee_email",
        "company",
        "grant_date",
        "cliff_date",
        "total_options",
        "strike_price",
        "grant_type",
        "status",
    )
    list_filter = ("grant_type", "status", "company")
    search_fields = ("employee_name", "employee_email", "company__name")
    ordering = ("-grant_date",)
