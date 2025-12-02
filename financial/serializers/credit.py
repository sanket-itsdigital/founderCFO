from rest_framework import serializers
from financial.models.credit import Credit


class CreditListSerializer(serializers.ModelSerializer):
    """Serializer for Credit list view with calculated fields"""
    current_balance = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True
    )
    current_balance_display = serializers.SerializerMethodField()
    utilization_percentage = serializers.FloatField(read_only=True)
    credit_limit_display = serializers.SerializerMethodField()
    risk_level_display = serializers.SerializerMethodField()
    payment_score_status = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = [
            "id",
            "customer_name",
            "credit_limit",
            "credit_limit_display",
            "current_balance",
            "current_balance_display",
            "utilization_percentage",
            "payment_score",
            "payment_score_status",
            "risk_level",
            "risk_level_display",
            "avg_days_to_pay",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_balance",
            "current_balance_display",
            "utilization_percentage",
            "payment_score",
            "payment_score_status",
            "risk_level",
            "risk_level_display",
            "avg_days_to_pay",
            "created_at",
            "updated_at",
        ]

    def get_current_balance_display(self, obj):
        """Format current balance in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        balance = obj.current_balance
        if balance == 0:
            return "₹0.00L"
        lakhs = balance / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_credit_limit_display(self, obj):
        """Format credit limit in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        if obj.credit_limit == 0:
            return "₹0.00L"
        lakhs = obj.credit_limit / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_risk_level_display(self, obj):
        """Get risk level display with color indicator"""
        risk_colors = {
            "Low": "#10B981",  # Green
            "Medium": "#F59E0B",  # Yellow/Amber
            "High": "#EF4444",  # Red
        }
        return {
            "label": obj.get_risk_level_display(),
            "value": obj.risk_level,
            "color": risk_colors.get(obj.risk_level, "#6B7280"),
        }

    def get_payment_score_status(self, obj):
        """Get payment score status (Healthy, Moderate, Poor)"""
        if obj.payment_score >= 80:
            return "Healthy"
        elif obj.payment_score >= 60:
            return "Moderate"
        else:
            return "Poor"


class CreditDetailSerializer(serializers.ModelSerializer):
    """Serializer for Credit detail view - allows updating credit_limit only"""
    current_balance = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True
    )
    current_balance_display = serializers.SerializerMethodField()
    utilization_percentage = serializers.FloatField(read_only=True)
    credit_limit_display = serializers.SerializerMethodField()
    risk_level_display = serializers.SerializerMethodField()
    payment_score_status = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = [
            "id",
            "customer_name",
            "credit_limit",
            "credit_limit_display",
            "current_balance",
            "current_balance_display",
            "utilization_percentage",
            "payment_score",
            "payment_score_status",
            "risk_level",
            "risk_level_display",
            "avg_days_to_pay",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer_name",
            "current_balance",
            "current_balance_display",
            "utilization_percentage",
            "payment_score",
            "payment_score_status",
            "risk_level",
            "risk_level_display",
            "avg_days_to_pay",
            "created_at",
            "updated_at",
        ]

    def get_current_balance_display(self, obj):
        """Format current balance in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        balance = obj.current_balance
        if balance == 0:
            return "₹0.00L"
        lakhs = balance / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_credit_limit_display(self, obj):
        """Format credit limit in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        if obj.credit_limit == 0:
            return "₹0.00L"
        lakhs = obj.credit_limit / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_risk_level_display(self, obj):
        """Get risk level display with color indicator"""
        risk_colors = {
            "Low": "#10B981",  # Green
            "Medium": "#F59E0B",  # Yellow/Amber
            "High": "#EF4444",  # Red
        }
        return {
            "label": obj.get_risk_level_display(),
            "value": obj.risk_level,
            "color": risk_colors.get(obj.risk_level, "#6B7280"),
        }

    def get_payment_score_status(self, obj):
        """Get payment score status (Healthy, Moderate, Poor)"""
        if obj.payment_score >= 80:
            return "Healthy"
        elif obj.payment_score >= 60:
            return "Moderate"
        else:
            return "Poor"

