from rest_framework import serializers


class DepartmentBreakdownSerializer(serializers.Serializer):
    department = serializers.CharField()
    headcount = serializers.IntegerField()
    percent_of_org = serializers.DecimalField(max_digits=6, decimal_places=2)
    avg_salary = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_tenure_years = serializers.DecimalField(max_digits=5, decimal_places=2)
    open_positions = serializers.IntegerField()


class LocationBreakdownSerializer(serializers.Serializer):
    location = serializers.CharField()
    headcount = serializers.IntegerField()
    percent_of_org = serializers.DecimalField(max_digits=6, decimal_places=2)
    departments = serializers.IntegerField()
    avg_salary = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_tenure_years = serializers.DecimalField(max_digits=5, decimal_places=2)
    open_positions = serializers.IntegerField()


class EmployeeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    department = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True)
    level = serializers.CharField(allow_null=True)
    salary_annual = serializers.DecimalField(max_digits=14, decimal_places=2)
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)


class DepartmentBreakdownResponseSerializer(serializers.Serializer):
    total_headcount = serializers.IntegerField()
    departments = serializers.IntegerField()
    locations = serializers.IntegerField()
    levels = serializers.IntegerField()
    breakdown = DepartmentBreakdownSerializer(many=True)


class LocationBreakdownResponseSerializer(serializers.Serializer):
    total_headcount = serializers.IntegerField()
    departments = serializers.IntegerField()
    locations = serializers.IntegerField()
    levels = serializers.IntegerField()
    breakdown = LocationBreakdownSerializer(many=True)


class EmployeeListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = EmployeeSerializer(many=True)
