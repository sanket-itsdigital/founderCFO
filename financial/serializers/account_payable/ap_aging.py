from rest_framework import serializers


class APAgeingBucketSerializer(serializers.Serializer):
    """Serializer for individual ageing bucket"""
    label = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    percentage = serializers.FloatField()


class APAgeingSummarySerializer(serializers.Serializer):
    """Serializer for AP Ageing Summary response"""
    total_ap = serializers.FloatField()
    total_ap_display = serializers.CharField()
    overdue_percentage = serializers.FloatField()
    portfolio_health = serializers.CharField()
    ageing_buckets = APAgeingBucketSerializer(many=True)

