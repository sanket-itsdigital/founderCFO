from rest_framework import serializers


class HRHealthSerializer(serializers.Serializer):
    """Serializer for HR Health metric"""

    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()
    display = serializers.CharField()


class MetricWithTargetSerializer(serializers.Serializer):
    """Serializer for metrics with target comparison"""

    value = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    target = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    status = serializers.CharField(allow_null=True, required=False)
    display = serializers.CharField(allow_null=True, required=False)


class HighLevelKPISerializer(serializers.Serializer):
    """Serializer for high-level KPI cards"""

    hr_health = HRHealthSerializer()
    total_headcount = serializers.IntegerField()
    turnover_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_to_hire = serializers.IntegerField(allow_null=True)
    cost_per_hire = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True
    )


class DetailedMetricSerializer(serializers.Serializer):
    """Serializer for detailed HR metrics"""

    total_headcount = serializers.IntegerField()
    turnover_rate = MetricWithTargetSerializer()
    retention_rate = MetricWithTargetSerializer()
    cost_per_hire = MetricWithTargetSerializer()
    time_to_hire = MetricWithTargetSerializer()
    average_tenure = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    gender_diversity = MetricWithTargetSerializer()
    hr_cost_ratio = serializers.CharField(allow_null=True, required=False)


class WorkforceCompositionItemSerializer(serializers.Serializer):
    """Serializer for workforce composition items"""

    employment_type = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class GenderDiversityItemSerializer(serializers.Serializer):
    """Serializer for gender diversity items"""

    gender = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class GenderDiversityDetailSerializer(serializers.Serializer):
    """Serializer for gender diversity details"""

    breakdown = serializers.ListField(child=GenderDiversityItemSerializer())
    target_female_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    current_female_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class HRDashboardSerializer(serializers.Serializer):
    """Serializer for HR Dashboard response"""

    high_level_kpis = HighLevelKPISerializer()
    detailed_metrics = DetailedMetricSerializer()
    workforce_composition = serializers.ListField(
        child=WorkforceCompositionItemSerializer()
    )
    gender_diversity = GenderDiversityDetailSerializer()
