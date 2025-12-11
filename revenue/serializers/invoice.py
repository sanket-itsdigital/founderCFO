from rest_framework import serializers
from revenue.models.invoice import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Revenue Invoice"""

    class Meta:
        model = Invoice
        ref_name = "RevenueInvoice"
        fields = [
            "id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "customer_name",
            "customer_gstin",
            "product_name",
            "service_type",
            "hsn_sac_code",
            "place_of_supply",
            "quantity",
            "unit_price",
            "taxable_value",
            "cgst_rate",
            "cgst_amount",
            "sgst_rate",
            "sgst_amount",
            "igst_rate",
            "igst_amount",
            "total_amount",
            "status",
            "payment_terms",
            "salesperson",
            "region",
            "territory",
            "department",
            "branch",
            "branch_gstin",
            "project_id",
            "project_name",
            "billing_type",
            "billable_hours",
            "is_recurring",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Revenue Invoice"""

    class Meta:
        model = Invoice
        ref_name = "RevenueInvoiceCreate"
        fields = [
            "invoice_number",
            "invoice_date",
            "due_date",
            "customer_name",
            "customer_gstin",
            "product_name",
            "service_type",
            "hsn_sac_code",
            "place_of_supply",
            "quantity",
            "unit_price",
            "taxable_value",
            "cgst_rate",
            "cgst_amount",
            "sgst_rate",
            "sgst_amount",
            "igst_rate",
            "igst_amount",
            "total_amount",
            "status",
            "payment_terms",
            "salesperson",
            "region",
            "territory",
            "department",
            "branch",
            "branch_gstin",
            "project_id",
            "project_name",
            "billing_type",
            "billable_hours",
            "is_recurring",
            "notes",
        ]


class InvoiceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Revenue Invoice"""

    class Meta:
        model = Invoice
        ref_name = "RevenueInvoiceUpdate"
        fields = [
            "invoice_number",
            "invoice_date",
            "due_date",
            "customer_name",
            "customer_gstin",
            "product_name",
            "service_type",
            "hsn_sac_code",
            "place_of_supply",
            "quantity",
            "unit_price",
            "taxable_value",
            "cgst_rate",
            "cgst_amount",
            "sgst_rate",
            "sgst_amount",
            "igst_rate",
            "igst_amount",
            "total_amount",
            "status",
            "payment_terms",
            "salesperson",
            "region",
            "territory",
            "department",
            "branch",
            "branch_gstin",
            "project_id",
            "project_name",
            "billing_type",
            "billable_hours",
            "is_recurring",
            "notes",
        ]
