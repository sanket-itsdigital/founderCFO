from rest_framework import serializers
from dataroom.models import Question


class QuestionSerializer(serializers.ModelSerializer):
    asked_by_email = serializers.CharField(source="asked_by.email", read_only=True)
    answer_by_email = serializers.CharField(source="answer_by.email", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "document",
            "question",
            "asked_by",
            "asked_by_email",
            "answer_by",
            "answer_by_email",
            "answer",
            "is_answered",
            "created_at",
            "updated_at",
        ]

    read_only_fields = [
        "id",
        "asked_by_email",
        "answer_by_email",
        "created_at",
        "updated_at",
    ]
