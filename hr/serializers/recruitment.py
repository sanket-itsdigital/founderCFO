from rest_framework import serializers


class RecruitmentKPISerializer(serializers.Serializer):
    """Serializer for recruitment KPI cards"""

    time_to_hire = serializers.IntegerField(allow_null=True)
    time_to_hire_display = serializers.CharField()
    cost_per_hire = serializers.DecimalField(max_digits=12, decimal_places=2)
    cost_per_hire_display = serializers.CharField()
    offer_acceptance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    offer_acceptance_display = serializers.CharField()
    open_positions = serializers.IntegerField()
    filled_positions = serializers.IntegerField()


class RecruitmentFunnelSerializer(serializers.Serializer):
    """Serializer for recruitment funnel stages"""

    applications_received = serializers.IntegerField()
    applications_received_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    interviews_conducted = serializers.IntegerField()
    interviews_conducted_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    interviews_conversion_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    offers_made = serializers.IntegerField()
    offers_made_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    offers_conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    offers_accepted = serializers.IntegerField()
    offers_accepted_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    acceptance_conversion_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class SourceEffectivenessSerializer(serializers.Serializer):
    """Serializer for source effectiveness breakdown"""

    source = serializers.CharField()
    applications = serializers.IntegerField()
    hires = serializers.IntegerField()
    conversion_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    cost_per_hire = serializers.DecimalField(max_digits=12, decimal_places=2)
    cost_per_hire_display = serializers.CharField()


class OpenPositionSerializer(serializers.Serializer):
    """Serializer for open positions"""

    job_title = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    positions = serializers.IntegerField()
    applications = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()


class RecruitmentDashboardSerializer(serializers.Serializer):
    """Serializer for complete recruitment dashboard response"""

    kpis = RecruitmentKPISerializer()
    funnel = RecruitmentFunnelSerializer()
    source_effectiveness = serializers.ListField(child=SourceEffectivenessSerializer())
    open_positions = serializers.ListField(child=OpenPositionSerializer())
