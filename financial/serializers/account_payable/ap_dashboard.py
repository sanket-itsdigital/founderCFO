from rest_framework import serializers


class APKPISerializer(serializers.Serializer):
    """Serializer for AP Key Performance Indicators"""
    total_payables = serializers.FloatField()
    total_payables_display = serializers.CharField()
    outstanding_balance_percentage = serializers.FloatField()
    dpo = serializers.IntegerField()  # Days Payable Outstanding
    avg_payment_time_percentage = serializers.FloatField()
    payment_efficiency = serializers.FloatField()
    on_time_payment_rate = serializers.FloatField()
    overdue_amount = serializers.FloatField()
    overdue_amount_display = serializers.CharField()
    overdue_bills_count = serializers.IntegerField()
    overdue_percentage = serializers.FloatField()
    discounts_captured = serializers.FloatField()
    discounts_captured_display = serializers.CharField()
    early_payment_savings_percentage = serializers.FloatField()
    total_bills = serializers.IntegerField()
    all_vendor_bills_percentage = serializers.FloatField()


class APHealthStatusSerializer(serializers.Serializer):
    """Serializer for AP Health Status"""
    status = serializers.CharField()  # Healthy, Needs Attention, Critical
    on_time_payment_rate = serializers.FloatField()
    status_message = serializers.CharField()


class AgeingDistributionSerializer(serializers.Serializer):
    """Serializer for ageing distribution"""
    current = serializers.FloatField()
    current_display = serializers.CharField()
    overdue = serializers.FloatField()
    overdue_display = serializers.CharField()


class KeyInsightSerializer(serializers.Serializer):
    """Serializer for key insight tag"""
    text = serializers.CharField()
    type = serializers.CharField()  # warning, info, success, danger
    color = serializers.CharField()


class AgeingBreakdownSerializer(serializers.Serializer):
    """Serializer for ageing breakdown"""
    current = serializers.FloatField()
    current_display = serializers.CharField()
    days_1_30 = serializers.FloatField()
    days_1_30_display = serializers.CharField()
    days_31_60 = serializers.FloatField()
    days_31_60_display = serializers.CharField()
    days_61_90 = serializers.FloatField()
    days_61_90_display = serializers.CharField()
    days_90_plus = serializers.FloatField()
    days_90_plus_display = serializers.CharField()


class APDashboardSerializer(serializers.Serializer):
    """Serializer for AP Dashboard response"""
    kpis = APKPISerializer()
    ap_health_status = APHealthStatusSerializer()
    ageing_distribution = AgeingDistributionSerializer()
    key_insights = serializers.ListField(child=KeyInsightSerializer())
    ageing_breakdown = AgeingBreakdownSerializer()

