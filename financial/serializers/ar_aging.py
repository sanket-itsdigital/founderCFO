from rest_framework import serializers


class AgeingBucketSerializer(serializers.Serializer):
    """Serializer for individual ageing bucket data"""
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    amount_display = serializers.CharField()  # Formatted as ₹XX.XXL
    percentage = serializers.FloatField()
    color = serializers.CharField()  # Color code for the bucket


class ARAgeingSummarySerializer(serializers.Serializer):
    """Serializer for AR Ageing Summary dashboard data"""
    total_ar = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_ar_display = serializers.CharField()  # Formatted as ₹XX.XXL
    overdue_percentage = serializers.FloatField()
    portfolio_health = serializers.CharField()  # e.g., "At Risk - Prioritize collections"
    ageing_buckets = AgeingBucketSerializer(many=True)

