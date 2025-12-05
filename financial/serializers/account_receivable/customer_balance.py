from rest_framework import serializers


class CustomerBalanceSerializer(serializers.Serializer):
    """Serializer for Customer Balance Summary data"""

    customer_name = serializers.CharField()
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_display = serializers.CharField()  # Formatted as ₹XX.XXL
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit_limit_display = serializers.CharField()  # Formatted as ₹XX.XXL
    utilization = serializers.FloatField()  # Utilization percentage
    invoices = serializers.IntegerField()  # Number of invoices
    avg_days = serializers.IntegerField()  # Average days outstanding


class CustomerBalanceSummarySerializer(serializers.Serializer):
    """Serializer for Customer Balance Summary response"""

    total_customers = serializers.IntegerField()
    customers = CustomerBalanceSerializer(many=True)
    summary = (
        serializers.DictField()
    )  # Summary cards: total_outstanding, high_utilization, slow_payers


class CustomerBalanceDetailSerializer(serializers.Serializer):
    """Serializer for individual customer balance detail"""
    customer_name = serializers.CharField()
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_display = serializers.CharField()
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit_limit_display = serializers.CharField()
    utilization = serializers.FloatField()
    invoices = serializers.IntegerField()
    avg_days = serializers.IntegerField()
    payment_score = serializers.IntegerField(required=False)
    risk_level = serializers.CharField(required=False)
    avg_days_to_pay = serializers.IntegerField(required=False)


class CustomerBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for updating customer balance/credit information"""
    credit_limit = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        help_text="Credit limit for the customer"
    )
    payment_score = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        help_text="Payment score out of 100"
    )
    risk_level = serializers.ChoiceField(
        choices=["Low", "Medium", "High"],
        required=False,
        help_text="Risk level for the customer"
    )
