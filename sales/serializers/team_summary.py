from rest_framework import serializers


class TeamSummaryCardsSerializer(serializers.Serializer):
    """Serializer for Team Summary Cards response"""

    top_performer = serializers.DictField()
    team_avg_attainment = serializers.DictField()
    total_deals_closed = serializers.DictField()
    reps_at_above_quota = serializers.DictField()
