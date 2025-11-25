from rest_framework import serializers
from compliance.models import ComplianceTaskMaster


class ComplianceTaskMasterSerializer(serializers.ModelSerializer):
    task_id = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    next_due_date = serializers.DateField(read_only=True)
    reminder_days = serializers.IntegerField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ComplianceTaskMaster
        fields = [
            "id",
            "task_id",
            "act",
            "particulars",
            "due_date",
            "frequency",
            "severity",
            "status",
            "company_type",
            "assignee",
            "last_filed_date",
            "next_due_date",
            "completed_date",
            "reminder_days",
            "penalty_amount",
            "payment_amount",
            "payment_reference",
            "consequences",
            "notes",
            "evidence_url",
            "days_until_due",
            "is_overdue",
            "interest_percentage",
            "penalty",
            "late_fee",
            "interest_amount",
            "is_admin_created",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "task_id",
            "status",
            "next_due_date",
            "reminder_days",
            "days_until_due",
            "is_overdue",
            "is_admin_created",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
