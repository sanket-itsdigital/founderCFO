from rest_framework import serializers
from financial.models.disputes import Dispute
from financial.models.account_receivable import Invoice


class DisputeSerializer(serializers.ModelSerializer):
    """Serializer for Dispute"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    priority_color = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.SerializerMethodField()
    disputed_amount_display = serializers.SerializerMethodField()
    created_date_display = serializers.SerializerMethodField()

    class Meta:
        model = Dispute
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "customer_name",
            "reason",
            "reason_display",
            "disputed_amount",
            "disputed_amount_display",
            "priority",
            "priority_display",
            "priority_color",
            "status",
            "status_display",
            "status_color",
            "description",
            "resolution_notes",
            "resolved_at",
            "created_at",
            "created_date_display",
            "updated_at",
        ]

    def get_priority_color(self, obj):
        colors = {
            "Low": "#10B981",  # Green
            "Medium": "#3B82F6",  # Blue
            "High": "#F59E0B",  # Orange
            "Urgent": "#EF4444",  # Red
        }
        return colors.get(obj.priority, "#6B7280")

    def get_status_color(self, obj):
        colors = {
            "Open": "#EF4444",  # Red
            "In Review": "#F59E0B",  # Orange
            "Resolved": "#10B981",  # Green
            "Closed": "#6B7280",  # Grey
        }
        return colors.get(obj.status, "#6B7280")

    def get_disputed_amount_display(self, obj):
        if obj.disputed_amount >= 1000:
            return f"₹{obj.disputed_amount / 1000:.2f}K"
        return f"₹{obj.disputed_amount:.2f}"

    def get_created_date_display(self, obj):
        return obj.created_at.strftime("%m/%d/%Y")


class DisputeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Dispute"""
    class Meta:
        model = Dispute
        fields = [
            "invoice",
            "reason",
            "disputed_amount",
            "priority",
            "description",
        ]

