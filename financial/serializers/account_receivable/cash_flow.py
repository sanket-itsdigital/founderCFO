from rest_framework import serializers


class CashFlowProjectionDataSerializer(serializers.Serializer):
    """Serializer for individual projection data point"""
    projection_date = serializers.DateField()
    date_display = serializers.CharField()
    due_amount = serializers.FloatField()
    due_amount_display = serializers.CharField()
    expected_collection = serializers.FloatField()
    expected_collection_display = serializers.CharField()
    optimistic_collection = serializers.FloatField()
    optimistic_collection_display = serializers.CharField()
    conservative_collection = serializers.FloatField()
    conservative_collection_display = serializers.CharField()


class CashFlowProjectionSummarySerializer(serializers.Serializer):
    """Serializer for cash flow projection summary"""
    next_30_days = serializers.FloatField()
    next_30_days_display = serializers.CharField()
    next_60_days = serializers.FloatField()
    next_60_days_display = serializers.CharField()
    next_90_days = serializers.FloatField()
    next_90_days_display = serializers.CharField()
    total_due = serializers.FloatField()
    total_due_display = serializers.CharField()


class CashFlowRiskAnalysisSerializer(serializers.Serializer):
    """Serializer for cash flow risk analysis"""
    collection_rate_assumption = serializers.CharField()
    high_risk_invoices = serializers.IntegerField()
    high_risk_invoices_display = serializers.CharField()
    expected_vs_total_due = serializers.CharField()


class CashFlowProjectionResponseSerializer(serializers.Serializer):
    """Main serializer for Cash Flow Projection API response"""
    summary = CashFlowProjectionSummarySerializer()
    projections = serializers.ListField(child=CashFlowProjectionDataSerializer())
    risk_analysis = CashFlowRiskAnalysisSerializer()
    projection_type = serializers.CharField()
