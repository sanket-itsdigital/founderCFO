from rest_framework import serializers
from dataroom.models import Folder


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
