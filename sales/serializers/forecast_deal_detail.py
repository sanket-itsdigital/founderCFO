from rest_framework import serializers


class ForecastDealDetailSerializer(serializers.Serializer):
    """Serializer for forecast deal detail row"""

    account = serializers.CharField()
    owner = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    stage = serializers.CharField()
    category = serializers.CharField()  # commit, best_case, pipeline, upside
    confidence = serializers.CharField()  # high, medium, low
    close_date = serializers.DateField()
    close_date_display = serializers.CharField()
    risk = serializers.IntegerField()  # Risk level (1, 2, 3, etc.)


class ForecastDealDetailResponseSerializer(serializers.Serializer):
    """Serializer for Forecast Deal Detail response"""

    title = serializers.CharField()
    subtitle = serializers.CharField()
    deals = serializers.ListField(child=ForecastDealDetailSerializer())
