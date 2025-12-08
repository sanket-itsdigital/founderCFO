from rest_framework import serializers


class OverviewMetricsSerializer(serializers.Serializer):
    """Serializer for overview metrics"""

    total_headcount = serializers.IntegerField()
    total_departments = serializers.IntegerField()
    total_locations = serializers.IntegerField()


class DepartmentHeadcountSerializer(serializers.Serializer):
    """Serializer for department headcount data"""

    department_name = serializers.CharField()
    headcount = serializers.IntegerField()
    percentage_of_total = serializers.FloatField()
    average_tenure_years = serializers.FloatField(allow_null=True, required=False)


class LocationHeadcountSerializer(serializers.Serializer):
    """Serializer for location headcount data"""

    location_name = serializers.CharField()
    headcount = serializers.IntegerField()
    percentage = serializers.FloatField()


class LevelDistributionSerializer(serializers.Serializer):
    """Serializer for level distribution data"""

    level_name = serializers.CharField()
    headcount = serializers.IntegerField()
    percentage = serializers.FloatField()


class HeadcountOverviewSerializer(serializers.Serializer):
    """Serializer for Headcount Overview response"""

    overview = OverviewMetricsSerializer()
    headcount_by_department = serializers.ListField(
        child=DepartmentHeadcountSerializer()
    )
    headcount_by_location = serializers.ListField(child=LocationHeadcountSerializer())
    level_distribution = serializers.ListField(child=LevelDistributionSerializer())
