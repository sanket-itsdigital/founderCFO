from django.contrib import admin
from revenue.models.invoice import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_number",
        "invoice_date",
        "customer_name",
        "product_name",
        "service_type",
        "total_amount",
        "status",
        "salesperson",
        "created_at",
    )
    search_fields = (
        "invoice_number",
        "customer_name",
        "product_name",
        "service_type",
        "salesperson",
        "project_name",
    )
    list_filter = (
        "status",
        "service_type",
        "region",
        "territory",
        "department",
        "is_recurring",
        "invoice_date",
        "created_at",
    )
    ordering = ("-invoice_date",)
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
                    "invoice_number",
                    "invoice_date",
                    "due_date",
                    "status",
                    "payment_terms",
                )
            },
        ),
        (
            "Customer Information",
            {
                "fields": (
                    "customer_name",
                    "customer_gstin",
                )
            },
        ),
        (
            "Product/Service Information",
            {
                "fields": (
                    "product_name",
                    "service_type",
                    "hsn_sac_code",
                    "place_of_supply",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "quantity",
                    "unit_price",
                    "taxable_value",
                )
            },
        ),
        (
            "GST Details",
            {
                "fields": (
                    "cgst_rate",
                    "cgst_amount",
                    "sgst_rate",
                    "sgst_amount",
                    "igst_rate",
                    "igst_amount",
                )
            },
        ),
        (
            "Amounts",
            {"fields": ("total_amount",)},
        ),
        (
            "Sales Information",
            {
                "fields": (
                    "salesperson",
                    "region",
                    "territory",
                    "department",
                )
            },
        ),
        (
            "Branch Information",
            {
                "fields": (
                    "branch",
                    "branch_gstin",
                )
            },
        ),
        (
            "Project Information",
            {
                "fields": (
                    "project_id",
                    "project_name",
                )
            },
        ),
        (
            "Billing Information",
            {
                "fields": (
                    "billing_type",
                    "billable_hours",
                    "is_recurring",
                )
            },
        ),
        (
            "Additional Information",
            {"fields": ("notes",)},
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
