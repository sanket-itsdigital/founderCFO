from rest_framework import serializers
from financial.models.cash_flow import CashFlowProjection


class CashFlowProjectionSerializer(serializers.ModelSerializer):
    """Serializer for Cash Flow Projection"""
    due_amount_display = serializers.SerializerMethodField()
    expected_collection_display = serializers.SerializerMethodField()
    optimistic_collection_display = serializers.SerializerMethodField()
    conservative_collection_display = serializers.SerializerMethodField()
    date_display = serializers.SerializerMethodField()

    class Meta:
        model = CashFlowProjection
        fields = [
            "id",
            "projection_date",
            "date_display",
            "due_amount",
            "due_amount_display",
            "expected_collection",
            "expected_collection_display",
            "optimistic_collection",
            "optimistic_collection_display",
            "conservative_collection",
            "conservative_collection_display",
            "projection_type",
        ]

    def get_due_amount_display(self, obj):
        from decimal import Decimal
        if obj.due_amount == 0:
            return "₹0.00L"
        lakhs = obj.due_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_expected_collection_display(self, obj):
        from decimal import Decimal
        if obj.expected_collection == 0:
            return "₹0.00L"
        lakhs = obj.expected_collection / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_optimistic_collection_display(self, obj):
        from decimal import Decimal
        if obj.optimistic_collection == 0:
            return "₹0.00L"
        lakhs = obj.optimistic_collection / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_conservative_collection_display(self, obj):
        from decimal import Decimal
        if obj.conservative_collection == 0:
            return "₹0.00L"
        lakhs = obj.conservative_collection / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_date_display(self, obj):
        return obj.projection_date.strftime("%b %d")

