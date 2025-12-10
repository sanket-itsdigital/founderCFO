from django.contrib import admin

from financial.models import (
    AuditTrail,
    BankTransaction,
    BillPayment,
    CashFlowProjection,
    Credit,
    Dispute,
    DiscountProgram,
    DunningQueue,
    EmailTemplate,
    FactoringRequest,
    FactoringRequestInvoice,
    # Invoice,  # Moved to revenue app
    PaymentPlan,
    PaymentPlanInstallment,
    Vendor,
    Bill,
    WriteOff,
)
from financial.models.account_receivable.customer import Balance_summary


# Invoice admin has been moved to revenue app
# @admin.register(Invoice)
# class InvoiceAdmin(admin.ModelAdmin):
#     ...


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


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "name",
        "email",
        "phone",
        "contact_person",
        "gstin",
        "created_at",
    ]
    list_filter = ["created_at", "company"]
    search_fields = ["name", "email", "phone", "gstin", "pan", "contact_person"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "name", "contact_person", "email", "phone")},
        ),
        ("Address", {"fields": ("address",)}),
        ("Tax Information", {"fields": ("gstin", "pan")}),
        ("Additional", {"fields": ("payment_terms", "notes")}),
    )


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = [
        "company",
        "bill_number",
        "vendor",
        "vendor_name",
        "bill_date",
        "due_date",
        "amount",
        "paid_amount",
        "balance_amount",
        "status",
        "category",
        "created_at",
    ]
    list_filter = ["status", "category", "bill_date", "due_date", "created_at"]
    search_fields = ["bill_number", "vendor__name", "vendor_name", "category"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "balance_amount",
    ]
    date_hierarchy = "bill_date"
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "bill_number", "vendor", "vendor_name", "category")},
        ),
        ("Dates", {"fields": ("bill_date", "due_date")}),
        ("Amounts", {"fields": ("amount", "paid_amount", "balance_amount")}),
        ("Status", {"fields": ("status",)}),
        ("Additional", {"fields": ("notes",)}),
    )


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "customer_name",
        "credit_limit",
        "payment_score",
        "risk_level",
        "avg_days_to_pay",
        "created_at",
    ]
    list_filter = ["risk_level", "created_at", "company"]
    search_fields = ["customer_name", "company__name"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "current_balance",
        "utilization_percentage",
    ]
    fieldsets = (
        ("Basic Information", {"fields": ("company", "customer_name")}),
        (
            "Credit Details",
            {
                "fields": (
                    "credit_limit",
                    "payment_score",
                    "risk_level",
                    "avg_days_to_pay",
                )
            },
        ),
        (
            "Calculated Fields",
            {
                "fields": ("current_balance", "utilization_percentage"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "invoice",
        "number_of_installments",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "status",
        "start_date",
        "created_at",
    ]
    list_filter = ["status", "payment_frequency", "start_date", "created_at"]
    search_fields = [
        "invoice__invoice_number",
        "invoice__customer_name",
        "company__name",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "paid_amount",
        "remaining_amount",
        "progress_percentage",
    ]
    date_hierarchy = "start_date"


@admin.register(PaymentPlanInstallment)
class PaymentPlanInstallmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "payment_plan",
        "installment_number",
        "due_date",
        "amount",
        "status",
        "paid_at",
        "payment_reference",
        "created_at",
    ]
    list_filter = ["status", "due_date", "paid_at", "created_at"]
    search_fields = [
        "payment_plan__invoice__invoice_number",
        "payment_plan__invoice__customer_name",
        "payment_reference",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_overdue",
    ]
    date_hierarchy = "due_date"


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "company",
        "bill",
        "payment_date",
        "amount",
        "payment_method",
        "reference_number",
        "tds_deducted",
        "discount_taken",
        "created_at",
    ]
    list_filter = ["payment_method", "payment_date", "created_at", "company"]
    search_fields = [
        "bill__bill_number",
        "bill__vendor_name",
        "reference_number",
        "bank_name",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    date_hierarchy = "payment_date"
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("company", "bill", "payment_date", "amount", "payment_method")},
        ),
        ("Payment Details", {"fields": ("reference_number", "bank_name")}),
        ("Deductions", {"fields": ("tds_deducted", "discount_taken")}),
        ("Additional", {"fields": ("notes",)}),
    )
