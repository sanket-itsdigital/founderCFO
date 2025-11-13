from rest_framework import serializers
from dataroom.models import DocumentVersion


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "version_no",
            "file",
            "size_bytes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VersionCompareSerializer(serializers.Serializer):
    old_version_id = serializers.UUIDField()
    new_version_id = serializers.UUIDField()
