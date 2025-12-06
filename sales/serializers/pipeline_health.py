from rest_framework import serializers


class PipelineStageSerializer(serializers.Serializer):
    """Serializer for pipeline stage data"""
    stage = serializers.CharField()
    opportunities = serializers.IntegerField()
    pipeline_value = serializers.FloatField()
    pipeline_value_display = serializers.CharField()
    conversion_rate = serializers.FloatField()
    conversion_rate_display = serializers.CharField()
    health_percentage = serializers.FloatField()


class SalesPipelineHealthSerializer(serializers.Serializer):
    """Serializer for Sales Pipeline Health & Conversion response"""
    stages = serializers.ListField(child=PipelineStageSerializer())

