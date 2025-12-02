from rest_framework import serializers
from financial.models.dunning import DunningQueue, EmailTemplate
from financial.models.account_receivable import Invoice


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for EmailTemplate"""
    company_name = serializers.CharField(source='company.name', read_only=True, allow_null=True)

    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "subject",
            "body",
            "template_type",
            "is_active",
            "created_at",
            "updated_at",
        ]


class DunningQueueSerializer(serializers.ModelSerializer):
    """Serializer for DunningQueue"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    amount = serializers.DecimalField(source='invoice.balance_amount', max_digits=14, decimal_places=2, read_only=True)
    amount_display = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    stage_color = serializers.SerializerMethodField()

    class Meta:
        model = DunningQueue
        fields = [
            "id",
            "invoice_number",
            "customer_name",
            "amount",
            "amount_display",
            "days_overdue",
            "stage",
            "stage_display",
            "stage_color",
            "last_sent_at",
        ]

    def get_amount_display(self, obj):
        from decimal import Decimal
        amount = obj.invoice.balance_amount
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_stage_color(self, obj):
        colors = {
            "Friendly": "#3B82F6",  # Blue
            "Firm": "#F59E0B",  # Orange
            "Urgent": "#F97316",  # Light Orange
            "Final": "#EF4444",  # Red
        }
        return colors.get(obj.stage, "#6B7280")

