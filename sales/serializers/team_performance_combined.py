from rest_framework import serializers

from sales.serializers.team_performance import TeamPerformanceSerializer
from sales.serializers.revenue_by_product import RevenueByProductSerializer


class TeamPerformanceCombinedSerializer(serializers.Serializer):
    """Combined serializer for Team Performance and Revenue by Product"""
    team_performance = TeamPerformanceSerializer()
    revenue_by_product = RevenueByProductSerializer()

