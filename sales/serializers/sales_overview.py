from rest_framework import serializers


class SummaryCardSerializer(serializers.Serializer):
    """Serializer for summary card"""
    title = serializers.CharField()
    value = serializers.FloatField()
    value_display = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True, required=False)
    icon = serializers.CharField(allow_blank=True, required=False)
    gap = serializers.FloatField(allow_null=True, required=False)
    gap_display = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class PipelineHealthSerializer(serializers.Serializer):
    """Serializer for pipeline health"""
    health_score = serializers.IntegerField()
    health_status = serializers.CharField()
    open_deals = serializers.IntegerField()
    pipeline_value = serializers.FloatField()
    pipeline_value_display = serializers.CharField()
    avg_velocity = serializers.FloatField(allow_null=True, required=False)
    avg_velocity_display = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    stalled_deals = serializers.IntegerField()
    stalled_amount = serializers.FloatField(allow_null=True, required=False)
    stalled_amount_display = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    critical_count = serializers.IntegerField()


class KPICardSerializer(serializers.Serializer):
    """Serializer for KPI card"""
    title = serializers.CharField()
    value = serializers.CharField()
    value_display = serializers.CharField()
    subtitle = serializers.CharField()
    icon = serializers.CharField(allow_blank=True, required=False)
    icon_color = serializers.CharField(allow_blank=True, required=False)


class SalesFunnelStageSerializer(serializers.Serializer):
    """Serializer for sales funnel stage"""
    stage = serializers.CharField()
    deals_count = serializers.IntegerField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()


class SalesLeaderboardRepSerializer(serializers.Serializer):
    """Serializer for sales leaderboard rep"""
    rank = serializers.IntegerField()
    rep_name = serializers.CharField()
    deals_closed = serializers.IntegerField()
    revenue = serializers.FloatField()
    revenue_display = serializers.CharField()
    quota_attainment = serializers.FloatField()
    quota_attainment_display = serializers.CharField()


class PipelineOverviewDealSerializer(serializers.Serializer):
    """Serializer for pipeline overview deal"""
    deal_id = serializers.UUIDField()
    account_name = serializers.CharField()
    owner = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    product = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    mrr = serializers.FloatField()
    mrr_display = serializers.CharField()
    stage = serializers.CharField()
    probability = serializers.FloatField()
    probability_display = serializers.CharField()
    close_date = serializers.DateField(allow_null=True, required=False)
    close_date_display = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    status = serializers.CharField()


class SalesOverviewSerializer(serializers.Serializer):
    """Serializer for Sales Overview response"""
    summary_cards = serializers.ListField(child=SummaryCardSerializer())
    gap_card = SummaryCardSerializer(required=False)
    pipeline_health = PipelineHealthSerializer()
    kpi_cards = serializers.ListField(child=KPICardSerializer())
    sales_funnel = serializers.ListField(child=SalesFunnelStageSerializer())
    sales_leaderboard = serializers.ListField(child=SalesLeaderboardRepSerializer())
    pipeline_overview = serializers.DictField(required=False)

