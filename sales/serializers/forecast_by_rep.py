from rest_framework import serializers


class RepMetricsSerializer(serializers.Serializer):
    """Serializer for rep metrics"""

    closed = serializers.FloatField()
    closed_display = serializers.CharField()
    commit = serializers.FloatField()
    commit_display = serializers.CharField()
    best_case = serializers.FloatField()
    best_case_display = serializers.CharField()
    accuracy = serializers.FloatField()
    accuracy_display = serializers.CharField()


class RepForecastSerializer(serializers.Serializer):
    """Serializer for rep forecast data"""

    rep_name = serializers.CharField()
    quota = serializers.FloatField()
    quota_display = serializers.CharField()
    current_attainment = serializers.FloatField()
    current_attainment_display = serializers.CharField()
    closed_commit_percentage = serializers.FloatField()
    closed_commit_percentage_display = serializers.CharField()
    metrics = RepMetricsSerializer()


class ForecastByRepSerializer(serializers.Serializer):
    """Serializer for Forecast By Rep response"""

    reps = serializers.ListField(child=RepForecastSerializer())
