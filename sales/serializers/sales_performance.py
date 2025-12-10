from rest_framework import serializers


class SummaryMetricsSerializer(serializers.Serializer):
    """Serializer for summary metrics"""
    deals = serializers.IntegerField()
    reps = serializers.IntegerField()
    activities = serializers.IntegerField()


class ARRWaterfallDataSerializer(serializers.Serializer):
    """Serializer for ARR Waterfall data point"""
    month = serializers.CharField()
    new_revenue = serializers.FloatField()
    new_revenue_display = serializers.CharField()
    expansion = serializers.FloatField()
    expansion_display = serializers.CharField()
    churn = serializers.FloatField()
    churn_display = serializers.CharField()
    total_arr = serializers.FloatField()
    total_arr_display = serializers.CharField()


class ARRWaterfallSerializer(serializers.Serializer):
    """Serializer for ARR Growth Waterfall chart"""
    title = serializers.CharField()
    data = serializers.ListField(child=ARRWaterfallDataSerializer())


class SalesPerformanceDashboardSerializer(serializers.Serializer):
    """Serializer for Sales Performance Dashboard response"""
    summary_metrics = SummaryMetricsSerializer()
    arr_waterfall = ARRWaterfallSerializer()

