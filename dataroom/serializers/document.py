from rest_framework import serializers
from dataroom.models import Document, DocumentVersion


class DocumentSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source="folder.name", read_only=True)
    upload_date = serializers.DateTimeField(source="created_at", read_only=True)
    size = serializers.SerializerMethodField()
    questions_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "company",
            "folder",
            "folder_name",
            "name",
            "file",
            "size_bytes",
            "size",
            "access_notes",
            "views_count",
            "downloads_count",
            "upload_date",
            "questions_count",
        ]
        read_only_fields = [
            "id",
            "views_count",
            "downloads_count",
            "upload_date",
            "size",
        ]

    def get_size(self, obj):
        if obj.size_bytes is None:
            return None
        # return in human readable units
        kb = 1024.0
        mb = kb * 1024.0
        gb = mb * 1024.0
        if obj.size_bytes >= gb:
            return f"{obj.size_bytes / gb:.2f} GB"
        if obj.size_bytes >= mb:
            return f"{obj.size_bytes / mb:.2f} MB"
        if obj.size_bytes >= kb:
            return f"{obj.size_bytes / kb:.2f} KB"
        return f"{obj.size_bytes} B"


class DocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "company", "folder", "name", "file", "access_notes"]

    def create(self, validated_data):
        # size_bytes from uploaded file
        uploaded_file = validated_data.get("file")
        if uploaded_file:
            validated_data["size_bytes"] = uploaded_file.size
        document = super().create(validated_data)
        # create initial version as v1
        DocumentVersion.objects.create(
            document=document,
            version_no=1,
            file=document.file,
            size_bytes=document.size_bytes or 0,
            created_by=validated_data.get("created_by"),
        )
        return document
