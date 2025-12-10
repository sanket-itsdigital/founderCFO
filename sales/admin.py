from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from decimal import Decimal

from sales.models import Sales, SalesTeam
from sales.enums import SalesStageStatusChoices


class SalesInline(admin.TabularInline):
    """Inline admin for displaying sales within SalesTeam"""
    model = Sales
    extra = 0
    readonly_fields = (
        "deal_id",
        "deal_name",
        "client",
        "amount",
        "mrr",
        "stage",
        "probability",
        "close_date",
        "created_at",
    )
    fields = (
        "deal_id",
        "deal_name",
        "client",
        "amount",
        "mrr",
        "stage",
        "probability",
        "close_date",
    )
    can_delete = False
    show_change_link = True


@admin.register(SalesTeam)
class SalesTeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "email",
        "phone",
        "designation",
        "total_deals",
        "total_revenue",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "company", "designation", "created_at")
    search_fields = ("name", "email", "phone", "employee_id", "company__name")
    ordering = ("name",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "total_deals_count",
        "total_revenue_display",
        "active_deals_count",
        "closed_won_count",
    )
    date_hierarchy = "created_at"
    inlines = [SalesInline]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "company",
                    "name",
                    "email",
                    "phone",
                    "employee_id",
                    "designation",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "notes",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "total_deals_count",
                    "active_deals_count",
                    "closed_won_count",
                    "total_revenue_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                )
            },
        ),
    )

    def total_deals(self, obj):
        """Display total number of deals"""
        return obj.sales.count()
    total_deals.short_description = "Total Deals"
    total_deals.admin_order_field = "sales__count"

    def total_revenue(self, obj):
        """Display total revenue from all deals"""
        total = obj.sales.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return f"₹{total:,.2f}"
    total_revenue.short_description = "Total Revenue"

    def total_deals_count(self, obj):
        """Read-only field for total deals count"""
        return obj.sales.count()
    total_deals_count.short_description = "Total Deals"

    def active_deals_count(self, obj):
        """Count of active deals (not closed won/lost)"""
        return obj.sales.exclude(
            stage__in=[
                SalesStageStatusChoices.CLOSED_WON,
                SalesStageStatusChoices.CLOSED_LOST,
            ]
        ).count()
    active_deals_count.short_description = "Active Deals"

    def closed_won_count(self, obj):
        """Count of closed won deals"""
        return obj.sales.filter(stage=SalesStageStatusChoices.CLOSED_WON).count()
    closed_won_count.short_description = "Closed Won"

    def total_revenue_display(self, obj):
        """Read-only field for total revenue display"""
        total = obj.sales.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return f"₹{total:,.2f}"
    total_revenue_display.short_description = "Total Revenue"

    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        qs = super().get_queryset(request)
        return qs.select_related("company").prefetch_related("sales")


@admin.register(Sales)
class SalesAdmin(admin.ModelAdmin):
    list_display = (
        "deal_name",
        "deal_id",
        "company",
        "client",
        "sales_team",
        "amount_display",
        "mrr_display",
        "stage",
        "probability_display",
        "close_date",
        "source",
        "created_at",
    )
    list_filter = (
        "stage",
        "source",
        "subscription_product",
        "company",
        "sales_team",
        "created_at",
        "close_date",
    )
    search_fields = (
        "deal_name",
        "deal_id",
        "client",
        "sales_team__name",
        "sales_team__email",
        "company__name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "arr_display",
        "days_in_stage_display",
    )
    date_hierarchy = "created_at"
    list_per_page = 50
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "company",
                    "deal_id",
                    "deal_name",
                    "client",
                    "sales_team",
                )
            },
        ),
        (
            "Deal Details",
            {
                "fields": (
                    "amount",
                    "mrr",
                    "arr_display",
                    "stage",
                    "probability",
                    "close_date",
                    "subscription_product",
                    "contract_term_months",
                )
            },
        ),
        (
            "Sales Process",
            {
                "fields": (
                    "source",
                    "next_step",
                    "days_in_stage",
                    "days_in_stage_display",
                    "last_activity",
                )
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "lost_reason",
                    "competitors",
                    "notes",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                )
            },
        ),
    )

    def amount_display(self, obj):
        """Display formatted amount"""
        return f"₹{obj.amount:,.2f}"
    amount_display.short_description = "Amount"
    amount_display.admin_order_field = "amount"

    def mrr_display(self, obj):
        """Display formatted MRR"""
        if obj.mrr:
            return f"₹{obj.mrr:,.2f}"
        return "-"
    mrr_display.short_description = "MRR"
    mrr_display.admin_order_field = "mrr"

    def probability_display(self, obj):
        """Display probability with color coding"""
        if obj.probability >= 75:
            color = "green"
        elif obj.probability >= 50:
            color = "orange"
        else:
            color = "red"
        probability_str = f"{obj.probability:.1f}%"
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            probability_str,
        )
    probability_display.short_description = "Probability"
    probability_display.admin_order_field = "probability"

    def arr_display(self, obj):
        """Display Annual Recurring Revenue (MRR * 12)"""
        if obj.mrr:
            arr = obj.mrr * Decimal("12")
            return f"₹{arr:,.2f}"
        return "-"
    arr_display.short_description = "ARR (Annual)"

    def days_in_stage_display(self, obj):
        """Display days in stage with color coding"""
        if obj.days_in_stage > 30:
            color = "red"
        elif obj.days_in_stage > 14:
            color = "orange"
        else:
            color = "green"
        days_str = f"{obj.days_in_stage} days"
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            days_str,
        )
    days_in_stage_display.short_description = "Days in Stage"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("company", "sales_team", "created_by", "updated_by")
