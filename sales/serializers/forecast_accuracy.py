from rest_framework import serializers


class ForecastVsActualDataSerializer(serializers.Serializer):
    """Serializer for forecast vs actual data point"""

    period = serializers.CharField()  # e.g., "Q1 FY25", "Oct 2024"
    forecast = serializers.FloatField()
    forecast_display = serializers.CharField()
    actual = serializers.FloatField()
    actual_display = serializers.CharField()


class ForecastVsActualSerializer(serializers.Serializer):
    """Serializer for forecast vs actual chart"""

    title = serializers.CharField()
    subtitle = serializers.CharField()
    data = serializers.ListField(child=ForecastVsActualDataSerializer())


class AccuracyTrendDataSerializer(serializers.Serializer):
    """Serializer for accuracy trend data point"""

    period = serializers.CharField()
    accuracy = serializers.FloatField()


class AccuracyTrendSerializer(serializers.Serializer):
    """Serializer for accuracy trend chart"""

    title = serializers.CharField()
    subtitle = serializers.CharField()
    data = serializers.ListField(child=AccuracyTrendDataSerializer())


class AccuracySummaryRowSerializer(serializers.Serializer):
    """Serializer for accuracy summary table row"""

    period = serializers.CharField()
    forecast = serializers.FloatField()
    forecast_display = serializers.CharField()
    actual = serializers.FloatField()
    actual_display = serializers.CharField()
    variance = serializers.FloatField()
    variance_display = serializers.CharField()
    accuracy = serializers.FloatField()
    accuracy_display = serializers.CharField()


class AccuracySummarySerializer(serializers.Serializer):
    """Serializer for accuracy summary table"""

    title = serializers.CharField()
    data = serializers.ListField(child=AccuracySummaryRowSerializer())


class ForecastAccuracySerializer(serializers.Serializer):
    """Serializer for Forecast Accuracy response"""

    forecast_vs_actual = ForecastVsActualSerializer()
    accuracy_trend = AccuracyTrendSerializer()
    accuracy_summary = AccuracySummarySerializer()
