from rest_framework import serializers


class OverviewSerializer(serializers.Serializer):
    total_documents = serializers.IntegerField()
    total_storage_bytes = serializers.IntegerField()
    total_views = serializers.IntegerField()
    downloads = serializers.IntegerField()
    active_users = serializers.IntegerField()
    avg_response_time_hours = serializers.FloatField()

    analytics = serializers.DictField(child=serializers.JSONField(), required=False)
