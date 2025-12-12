from rest_framework import serializers


class APKPISerializer(serializers.Serializer):
    """Serializer for AP Key Performance Indicators"""

    total_payables = serializers.FloatField()
    total_payables_display = serializers.CharField()
    outstanding_balance_percentage = serializers.FloatField()
    dpo = serializers.IntegerField()  # Days Payable Outstanding
    dpo_target = serializers.IntegerField(required=False)
    dpo_above_benchmark = serializers.FloatField(required=False)
    avg_payment_time_percentage = serializers.FloatField(required=False)
    payment_efficiency = serializers.FloatField()
    on_time_payment_rate = serializers.FloatField()
    overdue_amount = serializers.FloatField()
    overdue_amount_display = serializers.CharField()
    overdue_bills_count = serializers.IntegerField()
    overdue_percentage = serializers.FloatField()
    total_gst_payable = serializers.FloatField(required=False)
    total_gst_payable_display = serializers.CharField(required=False)
    cgst_amount = serializers.FloatField(required=False)
    cgst_amount_display = serializers.CharField(required=False)
    sgst_amount = serializers.FloatField(required=False)
    sgst_amount_display = serializers.CharField(required=False)
    igst_amount = serializers.FloatField(required=False)
    igst_amount_display = serializers.CharField(required=False)
    itc_available = serializers.FloatField(required=False)
    itc_available_display = serializers.CharField(required=False)
    itc_pending = serializers.FloatField(required=False)
    itc_pending_display = serializers.CharField(required=False)
    tds_payable = serializers.FloatField(required=False)
    tds_payable_display = serializers.CharField(required=False)
    tds_total = serializers.FloatField(required=False)
    tds_total_display = serializers.CharField(required=False)
    net_payable = serializers.FloatField(required=False)
    net_payable_display = serializers.CharField(required=False)
    avg_days_delinquent = serializers.IntegerField(required=False)
    payment_trend_mom = serializers.FloatField(required=False)
    payment_trend_mom_display = serializers.CharField(required=False)
    payment_trend_mom_percentage = serializers.FloatField(required=False)
    last_month_payments = serializers.FloatField(required=False)
    last_month_payments_display = serializers.CharField(required=False)
    discounts_captured = serializers.FloatField()
    discounts_captured_display = serializers.CharField()
    early_payment_savings_percentage = serializers.FloatField(required=False)
    vendor_concentration = serializers.FloatField(required=False)
    vendor_concentration_risk = serializers.CharField(required=False)
    total_bills = serializers.IntegerField()
    avg_bill_value = serializers.FloatField(required=False)
    avg_bill_value_display = serializers.CharField(required=False)
    all_vendor_bills_percentage = serializers.FloatField(required=False)


class APHealthStatusSerializer(serializers.Serializer):
    """Serializer for AP Health Status"""

    status = serializers.CharField()  # Healthy, Needs Attention, Critical
    on_time_payment_rate = serializers.FloatField()
    avg_days_delinquent = serializers.IntegerField(required=False)
    status_message = serializers.CharField()


class GSTSummarySerializer(serializers.Serializer):
    """Serializer for GST Summary"""

    total_gst = serializers.FloatField()
    total_gst_display = serializers.CharField()
    cgst = serializers.FloatField()
    cgst_display = serializers.CharField()
    sgst = serializers.FloatField()
    sgst_display = serializers.CharField()
    igst = serializers.FloatField()
    igst_display = serializers.CharField()
    itc_available = serializers.FloatField()
    itc_available_display = serializers.CharField()
    itc_status = serializers.CharField()


class TDSSectionSerializer(serializers.Serializer):
    """Serializer for TDS by section"""

    section = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    bill_count = serializers.IntegerField()


class TDSSummarySerializer(serializers.Serializer):
    """Serializer for TDS Summary"""

    total_tds = serializers.FloatField()
    total_tds_display = serializers.CharField()
    tds_payable = serializers.FloatField()
    tds_payable_display = serializers.CharField()
    by_section = TDSSectionSerializer(many=True)


class CashOutflowProjectionsSerializer(serializers.Serializer):
    """Serializer for Cash Outflow Projections"""

    this_week = serializers.FloatField()
    this_week_display = serializers.CharField()
    days_30 = serializers.FloatField()
    days_30_display = serializers.CharField()
    days_60 = serializers.FloatField()
    days_60_display = serializers.CharField()
    days_90 = serializers.FloatField()
    days_90_display = serializers.CharField()


class OverdueBreakdownSerializer(serializers.Serializer):
    """Serializer for overdue breakdown"""

    days_1_30 = serializers.FloatField()
    days_1_30_display = serializers.CharField()
    days_31_60 = serializers.FloatField()
    days_31_60_display = serializers.CharField()
    days_61_90 = serializers.FloatField()
    days_61_90_display = serializers.CharField()
    days_90_plus = serializers.FloatField()
    days_90_plus_display = serializers.CharField()


class AgeingDistributionSerializer(serializers.Serializer):
    """Serializer for ageing distribution"""

    current = serializers.FloatField()
    current_display = serializers.CharField()
    overdue = serializers.FloatField()
    overdue_display = serializers.CharField()
    overdue_breakdown = OverdueBreakdownSerializer(required=False)


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
    gst_summary = GSTSummarySerializer(required=False)
    tds_summary = TDSSummarySerializer(required=False)
    cash_outflow_projections = CashOutflowProjectionsSerializer(required=False)
    ageing_distribution = AgeingDistributionSerializer()
    key_insights = serializers.ListField(child=KeyInsightSerializer())
    ageing_breakdown = AgeingBreakdownSerializer()
