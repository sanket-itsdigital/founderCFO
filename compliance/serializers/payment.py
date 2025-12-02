from rest_framework import serializers
from compliance.models import CompliancePayments


class CompliancePaymentSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(read_only=True)
    task_id = serializers.CharField(read_only=True)
    related_act = serializers.CharField(read_only=True)
    due_date = serializers.DateField(read_only=True)
    days_early_or_late = serializers.IntegerField(read_only=True)
    is_late = serializers.BooleanField(read_only=True)
    compliance_task_id = serializers.UUIDField(
        source="compliance_task.id", read_only=True, allow_null=True
    )

    class Meta:
        model = CompliancePayments
        fields = [
            "id",
            "payment_id",
            "compliance_task",
            "compliance_task_id",
            "task_id",
            "payment_type",
            "period",
            "payment_date",
            "amount",
            "reference_number",
            "notes",
            "related_act",
            "due_date",
            "days_early_or_late",
            "is_late",
            "estimated_penalty",
            "estimated_interest",
            "estimated_late_fee",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payment_id",
            "task_id",
            "related_act",
            "due_date",
            "days_early_or_late",
            "is_late",
            "created_at",
            "updated_at",
        ]
