from rest_framework import serializers

from litigation.models import Case


class CaseSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source="company.id", read_only=True)

    class Meta:
        model = Case
        fields = (
            "id",
            "company_id",
            "case_number",
            "type",
            "synopsis",
            "total_exposure",
            "issue_date",
            "due_date",
            "status",
            "risk",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
