from rest_framework import serializers


class CohortDataSerializer(serializers.Serializer):
    """Serializer for cohort data point"""
    period = serializers.CharField()  # e.g., "Q1 2024"
    retention_percentage = serializers.FloatField()
    expansion_percentage = serializers.FloatField()
    churn_percentage = serializers.FloatField()


class CustomerCohortPerformanceSerializer(serializers.Serializer):
    """Serializer for Customer Cohort Performance response"""
    title = serializers.CharField()
    data = serializers.ListField(child=CohortDataSerializer())

