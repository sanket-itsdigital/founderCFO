from rest_framework import serializers
from financial.models.discounts import DiscountProgram
from financial.models.account_receivable import Invoice


class DiscountProgramSerializer(serializers.ModelSerializer):
    """Serializer for DiscountProgram"""
    annualized_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    description_text = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True, allow_null=True)

    class Meta:
        model = DiscountProgram
        fields = [
            "id",
            "company",
            "company_name",
            "program_name",
            "discount_percentage",
            "discount_days",
            "net_days",
            "is_active",
            "annualized_cost",
            "description_text",
            "created_at",
            "updated_at",
        ]


class EligibleInvoiceSerializer(serializers.Serializer):
    """Serializer for invoices eligible for early payment discount"""
    invoice_id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    customer_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    amount_display = serializers.CharField()
    best_discount = serializers.CharField()
    savings = serializers.DecimalField(max_digits=14, decimal_places=2)
    savings_display = serializers.CharField()
    deadline = serializers.DateField()
    deadline_display = serializers.CharField()

