from rest_framework import serializers


class CashFlowProjectionDataPointSerializer(serializers.Serializer):
    """Serializer for individual data point in cash flow projection"""
    date = serializers.DateField()
    date_display = serializers.CharField()
    due_amount = serializers.FloatField()
    due_amount_display = serializers.CharField()
    cumulative_amount = serializers.FloatField()
    cumulative_amount_display = serializers.CharField()


class CashFlowProjectionSummarySerializer(serializers.Serializer):
    """Serializer for cash flow projection summary"""
    next_7_days = serializers.FloatField()
    next_7_days_display = serializers.CharField()
    next_30_days = serializers.FloatField()
    next_30_days_display = serializers.CharField()
    next_90_days = serializers.FloatField()
    next_90_days_display = serializers.CharField()


class CashFlowProjectionSerializer(serializers.Serializer):
    """Serializer for cash flow projection response"""
    summary = CashFlowProjectionSummarySerializer()
    projections = CashFlowProjectionDataPointSerializer(many=True)

