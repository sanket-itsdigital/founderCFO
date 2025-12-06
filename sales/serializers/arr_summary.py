from rest_framework import serializers


class ARRSummaryCardSerializer(serializers.Serializer):
    """Serializer for ARR Summary Card"""
    title = serializers.CharField()
    value = serializers.FloatField()
    value_display = serializers.CharField()
    subtitle = serializers.CharField()


class ARRSummarySerializer(serializers.Serializer):
    """Serializer for ARR Summary response"""
    new_arr = ARRSummaryCardSerializer()
    expansion_arr = ARRSummaryCardSerializer()
    churned_arr = ARRSummaryCardSerializer()
    net_new_arr = ARRSummaryCardSerializer()

