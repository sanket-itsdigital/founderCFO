from decimal import Decimal
from rest_framework import serializers

from expense.models.budget import ExpenseBudget, BudgetPeriodTypeChoices


class ExpenseBudgetSerializer(serializers.ModelSerializer):
    """Serializer for ExpenseBudget model"""

    period_start = serializers.SerializerMethodField()
    period_end = serializers.SerializerMethodField()
    actual_amount = serializers.SerializerMethodField()
    variance = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseBudget
        fields = [
            "id",
            "category",
            "department",
            "period_type",
            "period",
            "period_start",
            "period_end",
            "budget_amount",
            "actual_amount",
            "variance",
            "utilization_percentage",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "period_start",
            "period_end",
            "actual_amount",
            "variance",
            "utilization_percentage",
            "status",
        ]

    def get_period_start(self, obj):
        """Get period start date"""
        return obj.get_period_start()

    def get_period_end(self, obj):
        """Get period end date"""
        return obj.get_period_end()

    def get_actual_amount(self, obj):
        """Calculate actual amount from bills"""
        return float(obj.calculate_actual_amount())

    def get_variance(self, obj):
        """Calculate variance"""
        return float(obj.get_variance())

    def get_utilization_percentage(self, obj):
        """Calculate utilization percentage"""
        return round(obj.get_utilization_percentage(), 1)

    def get_status(self, obj):
        """Get budget status"""
        return obj.get_status()


class ExpenseBudgetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ExpenseBudget"""

    class Meta:
        model = ExpenseBudget
        fields = [
            "category",
            "department",
            "period_type",
            "period",
            "budget_amount",
            "notes",
        ]

    def validate(self, attrs):
        """Validate budget data"""
        # Ensure period is first day of month for consistency
        period = attrs.get("period")
        if period:
            attrs["period"] = period.replace(day=1)
        return attrs

    def create(self, validated_data):
        """Create budget entry"""
        company = self.context["request"].user.company
        validated_data["company"] = company
        return ExpenseBudget.objects.create(**validated_data)


class ExpenseBudgetChoicesSerializer(serializers.Serializer):
    """Serializer for budget dropdown choices"""

    categories = serializers.ListField(
        child=serializers.CharField(), help_text="Available categories from bills"
    )
    departments = serializers.ListField(
        child=serializers.CharField(), help_text="Available departments from bills"
    )
    period_types = serializers.ListField(
        child=serializers.DictField(),
        help_text="Available period types with their display names",
    )

