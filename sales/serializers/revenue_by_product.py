from rest_framework import serializers


class ProductLineSerializer(serializers.Serializer):
    """Serializer for product line revenue data"""

    product = serializers.CharField()
    revenue = serializers.FloatField()
    revenue_display = serializers.CharField()
    deals_closed = serializers.IntegerField()
    avg_deal_size = serializers.FloatField()
    avg_deal_size_display = serializers.CharField()
    yoy_growth = serializers.FloatField(allow_null=True, required=False)
    yoy_growth_display = serializers.CharField(allow_null=True, required=False)


class RevenueByProductSerializer(serializers.Serializer):
    """Serializer for Revenue by Product Line response"""

    title = serializers.CharField()
    subtitle = serializers.CharField(required=False, allow_blank=True)
    product_lines = ProductLineSerializer(many=True)
    total = ProductLineSerializer()
