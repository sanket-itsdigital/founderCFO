from decimal import Decimal

from rest_framework import serializers


class BudgetKPISerializer(serializers.Serializer):
    """Serializer for Budget KPIs"""

    total_budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_budget_display = serializers.CharField()
    actual_spend = serializers.DecimalField(max_digits=14, decimal_places=2)
    actual_spend_display = serializers.CharField()
    variance = serializers.DecimalField(max_digits=14, decimal_places=2)
    variance_display = serializers.CharField()
    variance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    cost_per_employee = serializers.DecimalField(max_digits=14, decimal_places=2)
    cost_per_employee_display = serializers.CharField()
    active_employees = serializers.IntegerField()


class CategoryBudgetItemSerializer(serializers.Serializer):
    """Serializer for budget vs actual by category"""

    category = serializers.CharField()
    budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_display = serializers.CharField()
    actual = serializers.DecimalField(max_digits=14, decimal_places=2)
    actual_display = serializers.CharField()
    variance = serializers.DecimalField(max_digits=14, decimal_places=2)
    variance_display = serializers.CharField()
    variance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()


class DepartmentBudgetItemSerializer(serializers.Serializer):
    """Serializer for budget by department"""

    department = serializers.CharField()
    budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_display = serializers.CharField()
    actual = serializers.DecimalField(max_digits=14, decimal_places=2)
    actual_display = serializers.CharField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class MonthlySpendTrendItemSerializer(serializers.Serializer):
    """Serializer for monthly spend trend"""

    month = serializers.CharField()
    actual = serializers.DecimalField(max_digits=14, decimal_places=2)
    actual_display = serializers.CharField()
    budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_display = serializers.CharField()
    percentage = serializers.IntegerField()


class BudgetDashboardSerializer(serializers.Serializer):
    """Serializer for complete Budget Dashboard response"""

    kpis = BudgetKPISerializer()
    category_breakdown = serializers.ListField(child=CategoryBudgetItemSerializer())
    department_breakdown = serializers.ListField(child=DepartmentBudgetItemSerializer())
    monthly_trend = serializers.ListField(child=MonthlySpendTrendItemSerializer())
