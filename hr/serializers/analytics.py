from rest_framework import serializers


class DepartmentHeadcountSerializer(serializers.Serializer):
    """Serializer for headcount by department data"""

    department_name = serializers.CharField()
    headcount = serializers.IntegerField()


class LevelHeadcountSerializer(serializers.Serializer):
    """Serializer for headcount by level data"""

    level_name = serializers.CharField()
    headcount = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class MonthlyHiringSerializer(serializers.Serializer):
    """Serializer for monthly hiring trend data"""

    month = serializers.CharField()
    hiring_count = serializers.IntegerField()


class RecruitmentPipelineSerializer(serializers.Serializer):
    """Serializer for recruitment pipeline status data"""

    status = serializers.CharField()
    count = serializers.IntegerField()


class DepartmentSalarySerializer(serializers.Serializer):
    """Serializer for average salary by department data"""

    department_name = serializers.CharField()
    avg_salary = serializers.DecimalField(max_digits=12, decimal_places=2)


class BudgetActualSerializer(serializers.Serializer):
    """Serializer for budget vs actual data"""

    month = serializers.CharField()
    budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    actual = serializers.DecimalField(max_digits=15, decimal_places=2)


class AnalyticsSerializer(serializers.Serializer):
    """Serializer for Analytics Overview response"""

    headcount_by_department = serializers.ListField(
        child=DepartmentHeadcountSerializer()
    )
    headcount_by_level = serializers.ListField(child=LevelHeadcountSerializer())
    monthly_hiring_trend = serializers.ListField(child=MonthlyHiringSerializer())
    recruitment_pipeline = serializers.ListField(child=RecruitmentPipelineSerializer())
    avg_salary_by_department = serializers.ListField(child=DepartmentSalarySerializer())
    budget_vs_actual = serializers.ListField(child=BudgetActualSerializer())
