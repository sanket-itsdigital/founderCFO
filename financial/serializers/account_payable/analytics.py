from rest_framework import serializers


class SpendingByCategoryItemSerializer(serializers.Serializer):
    """Serializer for spending by category item"""
    category = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    percentage = serializers.FloatField()
    color = serializers.CharField(required=False)


class MonthlyTrendDataSerializer(serializers.Serializer):
    """Serializer for monthly trend data point"""
    month = serializers.CharField()
    month_display = serializers.CharField()
    billed = serializers.FloatField()
    billed_display = serializers.CharField()
    paid = serializers.FloatField()
    paid_display = serializers.CharField()


class TopVendorSerializer(serializers.Serializer):
    """Serializer for top vendor"""
    vendor_name = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()


class PaymentMethodItemSerializer(serializers.Serializer):
    """Serializer for payment method item"""
    payment_method = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    percentage = serializers.FloatField()
    color = serializers.CharField(required=False)


class APAnalyticsSerializer(serializers.Serializer):
    """Serializer for AP Analytics response"""
    spending_by_category = SpendingByCategoryItemSerializer(many=True)
    monthly_trend = MonthlyTrendDataSerializer(many=True)
    top_vendors = TopVendorSerializer(many=True)
    payment_methods = PaymentMethodItemSerializer(many=True)

