from rest_framework import serializers


class ForecastSummaryCardSerializer(serializers.Serializer):
    """Serializer for forecast summary card"""

    title = serializers.CharField()
    value = serializers.FloatField()
    value_display = serializers.CharField()
    subtitle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    icon = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ForecastWaterfallDataSerializer(serializers.Serializer):
    """Serializer for forecast waterfall data point"""

    category = serializers.CharField()  # Closed, Commit, Best Case, Pipeline
    value = serializers.FloatField()
    value_display = serializers.CharField()
    cumulative_value = serializers.FloatField()
    cumulative_value_display = serializers.CharField()


class ForecastWaterfallSerializer(serializers.Serializer):
    """Serializer for forecast waterfall chart"""

    title = serializers.CharField()
    subtitle = serializers.CharField()
    data = serializers.ListField(child=ForecastWaterfallDataSerializer())
    quota = serializers.FloatField()
    quota_display = serializers.CharField()


class MonthlyBreakdownDataSerializer(serializers.Serializer):
    """Serializer for monthly breakdown data point"""

    month = serializers.CharField()  # e.g., "Nov 2024"
    closed = serializers.FloatField()
    closed_display = serializers.CharField()
    commit = serializers.FloatField()
    commit_display = serializers.CharField()
    best_case = serializers.FloatField()
    best_case_display = serializers.CharField()
    pipeline = serializers.FloatField()
    pipeline_display = serializers.CharField()
    total = serializers.FloatField()
    total_display = serializers.CharField()


class MonthlyBreakdownSerializer(serializers.Serializer):
    """Serializer for monthly breakdown chart"""

    title = serializers.CharField()
    subtitle = serializers.CharField()
    data = serializers.ListField(child=MonthlyBreakdownDataSerializer())


class PipelineCoverageCardSerializer(serializers.Serializer):
    """Serializer for pipeline coverage card"""

    category = serializers.CharField()  # Commit, Best Case, Pipeline, Upside
    value = serializers.FloatField()
    value_display = serializers.CharField()
    deals = serializers.IntegerField()
    weighted_value = serializers.FloatField()
    weighted_value_display = serializers.CharField()


class PipelineCoverageSerializer(serializers.Serializer):
    """Serializer for pipeline coverage analysis"""

    title = serializers.CharField()
    coverage_multiplier = serializers.FloatField()
    coverage_display = serializers.CharField()
    cards = serializers.ListField(child=PipelineCoverageCardSerializer())


class SalesForecastSerializer(serializers.Serializer):
    """Serializer for Sales Forecast response"""

    period = serializers.CharField()  # e.g., "Q4 FY25"
    summary_cards = serializers.ListField(child=ForecastSummaryCardSerializer())
    forecast_waterfall = ForecastWaterfallSerializer()
    monthly_breakdown = MonthlyBreakdownSerializer()
    pipeline_coverage = PipelineCoverageSerializer()
