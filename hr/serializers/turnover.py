from rest_framework import serializers


class TurnoverKPISerializer(serializers.Serializer):
    """Serializer for turnover KPI cards"""

    turnover_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    turnover_rate_display = serializers.CharField()
    total_exits = serializers.IntegerField()
    total_exits_display = serializers.CharField()
    retention_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    retention_rate_display = serializers.CharField()
    avg_tenure = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_tenure_display = serializers.CharField()


class DepartmentTurnoverSerializer(serializers.Serializer):
    """Serializer for turnover by department"""

    department = serializers.CharField()
    total_employees = serializers.IntegerField()
    exits = serializers.IntegerField()
    turnover_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    turnover_rate_display = serializers.CharField()
    status = serializers.CharField()


class TenureRangeTurnoverSerializer(serializers.Serializer):
    """Serializer for turnover by tenure range"""

    tenure_range = serializers.CharField()
    exits = serializers.IntegerField()
    exit_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()


class ExitSummarySerializer(serializers.Serializer):
    """Serializer for exit summary"""

    active_employees = serializers.IntegerField()
    resigned = serializers.IntegerField()
    terminated = serializers.IntegerField()
    on_leave = serializers.IntegerField()


class TurnoverOverviewSerializer(serializers.Serializer):
    """Serializer for overall turnover overview"""

    kpis = TurnoverKPISerializer()
    exit_summary = ExitSummarySerializer()


class TurnoverByDepartmentResponseSerializer(serializers.Serializer):
    """Serializer for turnover by department response"""

    kpis = TurnoverKPISerializer()
    breakdown = serializers.ListField(child=DepartmentTurnoverSerializer())


class TurnoverByTenureResponseSerializer(serializers.Serializer):
    """Serializer for turnover by tenure response"""

    breakdown = serializers.ListField(child=TenureRangeTurnoverSerializer())


class TurnoverCompleteSerializer(serializers.Serializer):
    """Serializer for complete turnover data combining all views"""

    kpis = TurnoverKPISerializer()
    exit_summary = ExitSummarySerializer()
    by_department = serializers.ListField(child=DepartmentTurnoverSerializer())
    by_tenure = serializers.ListField(child=TenureRangeTurnoverSerializer())
