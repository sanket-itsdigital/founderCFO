from rest_framework import serializers
from sales.serializers.arr_summary import ARRSummaryCardSerializer
from sales.serializers.cohort_performance import CohortDataSerializer
from sales.serializers.pipeline_health import PipelineStageSerializer
from sales.serializers.sales_performance import (
    SummaryMetricsSerializer,
    ARRWaterfallDataSerializer,
)


class ARRSummarySerializer(serializers.Serializer):
    """Serializer for ARR Summary in combined response"""
    new_arr = ARRSummaryCardSerializer()
    expansion_arr = ARRSummaryCardSerializer()
    churned_arr = ARRSummaryCardSerializer()
    net_new_arr = ARRSummaryCardSerializer()


class CohortPerformanceSerializer(serializers.Serializer):
    """Serializer for Cohort Performance in combined response"""
    title = serializers.CharField()
    data = serializers.ListField(child=CohortDataSerializer())


class PipelineHealthSerializer(serializers.Serializer):
    """Serializer for Pipeline Health in combined response"""
    stages = serializers.ListField(child=PipelineStageSerializer())


class ARRWaterfallSerializer(serializers.Serializer):
    """Serializer for ARR Waterfall in combined response"""
    title = serializers.CharField()
    data = serializers.ListField(child=ARRWaterfallDataSerializer())


class SalesPerformanceSerializer(serializers.Serializer):
    """Serializer for Sales Performance in combined response"""
    summary_metrics = SummaryMetricsSerializer()
    arr_waterfall = ARRWaterfallSerializer()


class RevenueAnalyticsSerializer(serializers.Serializer):
    """Serializer for combined Revenue Analytics response"""
    arr_summary = ARRSummarySerializer()
    cohort_performance = CohortPerformanceSerializer()
    pipeline_health = PipelineHealthSerializer()
    sales_performance = SalesPerformanceSerializer()

