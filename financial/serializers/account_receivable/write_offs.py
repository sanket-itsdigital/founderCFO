from rest_framework import serializers
from financial.models.account_receivable.write_offs import WriteOff
from financial.models.account_receivable import Invoice


class WriteOffCandidateSerializer(serializers.Serializer):
    """Serializer for write-off candidate invoices"""
    invoice_id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    customer_name = serializers.CharField()
    invoice_date = serializers.DateField()
    due_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    amount_display = serializers.CharField()
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance_due_display = serializers.CharField()
    days_overdue = serializers.IntegerField()
    reason = serializers.CharField()


class WriteOffSerializer(serializers.ModelSerializer):
    """Serializer for WriteOff"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    write_off_amount_display = serializers.SerializerMethodField()
    write_off_date_display = serializers.SerializerMethodField()

    class Meta:
        model = WriteOff
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "customer_name",
            "write_off_amount",
            "write_off_amount_display",
            "reason",
            "write_off_date",
            "write_off_date_display",
            "notes",
            "created_at",
        ]

    def get_write_off_amount_display(self, obj):
        from decimal import Decimal
        if obj.write_off_amount == 0:
            return "₹0.00L"
        lakhs = obj.write_off_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_write_off_date_display(self, obj):
        return obj.write_off_date.strftime("%m/%d/%Y")

