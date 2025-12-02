from django.contrib import admin

from subscriptions.models import CompanySubscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "plan",
        "start_date",
        "end_date",
        "status",
        "amount_paid",
    )
    list_filter = ("status", "plan")
    search_fields = ("company__name", "plan__name")

