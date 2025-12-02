from rest_framework import serializers
from financial.models.reconcile import BankTransaction
from financial.models.account_receivable import Invoice


class BankTransactionSerializer(serializers.ModelSerializer):
    """Serializer for BankTransaction"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    amount_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    status_color = serializers.SerializerMethodField()
    matched_invoice_number = serializers.CharField(source='matched_invoice.invoice_number', read_only=True, allow_null=True)

    class Meta:
        model = BankTransaction
        fields = [
            "id",
            "transaction_date",
            "description",
            "amount",
            "amount_display",
            "transaction_type",
            "transaction_type_display",
            "reference_number",
            "is_matched",
            "status_display",
            "status_color",
            "matched_invoice",
            "matched_invoice_number",
            "matched_at",
            "created_at",
        ]

    def get_amount_display(self, obj):
        return f"₹{obj.amount:,.0f}"

    def get_status_display(self, obj):
        return "Matched" if obj.is_matched else "Unmatched"

    def get_status_color(self, obj):
        return "#10B981" if obj.is_matched else "#F59E0B"


class UnmatchedInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for unmatched invoices"""
    invoice_number = serializers.CharField()
    customer_name = serializers.CharField()
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance_display = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "customer_name",
            "balance",
            "balance_display",
        ]

    def get_balance_display(self, obj):
        return f"₹{obj.balance:,.0f}"

