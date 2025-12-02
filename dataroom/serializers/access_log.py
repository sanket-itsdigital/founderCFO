from rest_framework import serializers
from dataroom.models import AccessLog


class AccessLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    document_name = serializers.CharField(source="document.name", read_only=True)

    class Meta:
        model = AccessLog
        fields = [
            "id",
            "company",
            "user",
            "user_email",
            "document",
            "document_name",
            "action",
            "timestamp",
            "ip_address",
            "created_at",
        ]
        read_only_fields = ["id", "timestamp", "created_at"]
