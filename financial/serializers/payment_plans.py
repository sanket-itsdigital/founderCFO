from rest_framework import serializers
from financial.models.payment_plans import PaymentPlan, PaymentPlanInstallment
from financial.models.account_receivable import Invoice


class PaymentPlanInstallmentSerializer(serializers.ModelSerializer):
    """Serializer for PaymentPlanInstallment"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_display = serializers.SerializerMethodField()
    due_date_display = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaymentPlanInstallment
        fields = [
            "id",
            "installment_number",
            "due_date",
            "due_date_display",
            "amount",
            "amount_display",
            "status",
            "status_display",
            "is_overdue",
            "paid_at",
            "payment_reference",
        ]

    def get_amount_display(self, obj):
        from decimal import Decimal
        if obj.amount == 0:
            return "₹0.00L"
        lakhs = obj.amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_due_date_display(self, obj):
        return obj.due_date.strftime("%m/%d/%Y")


class PaymentPlanSerializer(serializers.ModelSerializer):
    """Serializer for PaymentPlan"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_frequency_display = serializers.CharField(source='get_payment_frequency_display', read_only=True)
    total_amount_display = serializers.SerializerMethodField()
    paid_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    paid_amount_display = serializers.SerializerMethodField()
    remaining_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    installments = PaymentPlanInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentPlan
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "customer_name",
            "number_of_installments",
            "payment_frequency",
            "payment_frequency_display",
            "total_amount",
            "total_amount_display",
            "paid_amount",
            "paid_amount_display",
            "remaining_amount",
            "progress_percentage",
            "status",
            "status_display",
            "start_date",
            "installments",
            "created_at",
            "updated_at",
        ]

    def get_total_amount_display(self, obj):
        from decimal import Decimal
        if obj.total_amount == 0:
            return "₹0.00L"
        lakhs = obj.total_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_paid_amount_display(self, obj):
        return f"₹{obj.paid_amount:.0f} paid"


class PaymentPlanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PaymentPlan"""
    class Meta:
        model = PaymentPlan
        fields = [
            "invoice",
            "number_of_installments",
            "payment_frequency",
            "start_date",
        ]

    def validate_invoice(self, value):
        """Validate invoice has minimum balance"""
        from decimal import Decimal
        balance = value.balance_amount
        if balance < Decimal("50000"):
            raise serializers.ValidationError("Invoice must have minimum balance of ₹50,000")
        return value

