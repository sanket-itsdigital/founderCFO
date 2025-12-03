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
