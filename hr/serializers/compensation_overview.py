from rest_framework import serializers


class OverviewMetricsSerializer(serializers.Serializer):
    """Serializer for compensation overview metrics"""

    avg_salary_annual = serializers.DecimalField(max_digits=12, decimal_places=2)
    median_salary_annual = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_payroll_annual = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_employees = serializers.IntegerField()
    total_benefits_annual = serializers.DecimalField(max_digits=15, decimal_places=2)
    benefits_percentage_of_payroll = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    bonus_pool_annual = serializers.DecimalField(max_digits=15, decimal_places=2)
    bonus_percentage_of_base = serializers.DecimalField(max_digits=5, decimal_places=2)


class DepartmentCompensationSerializer(serializers.Serializer):
    """Serializer for compensation by department data"""

    department_name = serializers.CharField()
    employees = serializers.IntegerField()
    avg_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    median = serializers.DecimalField(max_digits=12, decimal_places=2)
    min = serializers.DecimalField(max_digits=12, decimal_places=2)
    max = serializers.DecimalField(max_digits=12, decimal_places=2)


class SalaryByLevelSerializer(serializers.Serializer):
    """Serializer for salary by level data"""

    level_name = serializers.CharField()
    employee_count = serializers.IntegerField()
    total_salary = serializers.DecimalField(max_digits=15, decimal_places=2)
    percentage_of_total = serializers.DecimalField(max_digits=5, decimal_places=2)


class CompensationSummarySerializer(serializers.Serializer):
    """Serializer for compensation summary data"""

    base_salaries = serializers.DecimalField(max_digits=15, decimal_places=2)
    benefits = serializers.DecimalField(max_digits=15, decimal_places=2)
    bonus_pool = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_compensation = serializers.DecimalField(max_digits=15, decimal_places=2)


class CompensationOverviewSerializer(serializers.Serializer):
    """Serializer for Compensation Overview response"""

    overview = OverviewMetricsSerializer()
    compensation_by_department = serializers.ListField(
        child=DepartmentCompensationSerializer()
    )
    salary_by_level = serializers.ListField(child=SalaryByLevelSerializer())
    compensation_summary = CompensationSummarySerializer()
