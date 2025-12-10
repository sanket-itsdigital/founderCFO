from rest_framework import serializers


class TeamPerformanceRepSerializer(serializers.Serializer):
    """Serializer for individual sales rep performance"""

    rep_id = serializers.UUIDField()
    rep_name = serializers.CharField()
    designation = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    quota = serializers.FloatField()
    quota_display = serializers.CharField()
    achieved = serializers.FloatField()
    achieved_display = serializers.CharField()
    attainment = serializers.FloatField()
    attainment_display = serializers.CharField()
    deals = serializers.IntegerField()
    avg_deal_size = serializers.FloatField()
    avg_deal_size_display = serializers.CharField()
    win_rate = serializers.FloatField()
    win_rate_display = serializers.CharField()
    pipeline = serializers.FloatField()
    pipeline_display = serializers.CharField()
    rating = serializers.FloatField()
    rating_display = serializers.CharField()


class TeamPerformanceSerializer(serializers.Serializer):
    """Serializer for Team Performance Overview response"""

    title = serializers.CharField()
    subtitle = serializers.CharField(required=False, allow_blank=True)
    reps = TeamPerformanceRepSerializer(many=True)
