from django.contrib import admin

from financial.models import (
    AuditTrail,
    BankTransaction,
    CashFlowProjection,
    Dispute,
    DiscountProgram,
    DunningQueue,
    EmailTemplate,
    FactoringRequest,
    FactoringRequestInvoice,
    Invoice,
    WriteOff,
)
from financial.models.customer import Balance_summary


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "company",
        "invoice_number",
        "customer_name",
        "invoice_date",
        "due_date",
        "total_amount",
        "paid_amount",
        "status",
        "balance_amount",
    ]
    list_filter = ["status", "invoice_date", "due_date", "created_at"]
    search_fields = ["invoice_number", "customer_name", "customer_email"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "invoice_date"

 

@admin.register(DunningQueue)
class DunningQueueAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "invoice",
        "stage",
        "created_at",
        "last_sent_at",
    ]
    list_filter = ["stage", "created_at", "last_sent_at"]
    search_fields = ["invoice__invoice_number", "invoice__customer_name"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "created_at"


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "name",
        "subject",
        "template_type",
        "is_active",
        "created_at",
    ]
    list_filter = ["template_type", "is_active", "created_at"]
    search_fields = ["name", "subject"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "invoice",
        "reason",
        "status",
        "priority",
        "disputed_amount",
        "created_at",
    ]
    list_filter = ["status", "priority", "reason", "created_at"]
    search_fields = [
        "invoice__invoice_number",
        "invoice__customer_name",
        "description",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "created_at"
 
@admin.register(CashFlowProjection)
class CashFlowProjectionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "projection_date",
        "due_amount",
        "expected_collection",
        "projection_type",
        "created_at",
    ]
    list_filter = ["projection_type", "projection_date", "created_at"]
    search_fields = ["company__name"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "projection_date"


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "transaction_date",
        "amount",
        "transaction_type",
        "is_matched",
        "description",
        "created_at",
    ]
    list_filter = ["transaction_type", "is_matched", "transaction_date", "created_at"]
    search_fields = ["description", "reference_number"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "transaction_date"


@admin.register(DiscountProgram)
class DiscountProgramAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "program_name",
        "discount_percentage",
        "discount_days",
        "net_days",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["program_name"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "description",
        "annualized_cost_of_not_taking",
    ]


@admin.register(FactoringRequest)
class FactoringRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "status",
        "advance_rate",
        "factoring_fee",
        "total_receivables",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["company__name"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "created_at"


@admin.register(FactoringRequestInvoice)
class FactoringRequestInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "factoring_request",
        "invoice",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = [
        "invoice__invoice_number",
        "factoring_request__company__name",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "invoice",
        "reason",
        "write_off_amount",
        "write_off_date",
        "created_at",
    ]
    list_filter = ["reason", "write_off_date", "created_at"]
    search_fields = [
        "invoice__invoice_number",
        "invoice__customer_name",
        "notes",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "write_off_date"


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "action",
        "entity_type",
        "reference",
        "user",
        "created_at",
    ]
    list_filter = ["action", "entity_type", "created_at"]
    search_fields = [
        "reference",
        "details",
        "entity_id",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    date_hierarchy = "created_at"


@admin.register(Balance_summary)
class BalanceSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "customer_name",
        "outstanding_amount",
        "credit_limit",
        "utilized_credit",
        "invoice_count",
        "average_days",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["customer_name", "company__name"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "credit_utilization_percentage",
    ]
