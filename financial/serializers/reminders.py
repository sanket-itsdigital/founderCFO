from rest_framework import serializers
from financial.models.reminders import Reminder, ReminderRule
from financial.models.account_receivable import Invoice


class ReminderRuleSerializer(serializers.ModelSerializer):
    """Serializer for ReminderRule"""
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)

    class Meta:
        model = ReminderRule
        fields = [
            "id",
            "rule_name",
            "trigger_days",
            "trigger_type",
            "trigger_type_display",
            "email_template_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ReminderScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Reminder Schedule"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    customer_email = serializers.SerializerMethodField()
    amount = serializers.DecimalField(source='invoice.total_amount', max_digits=14, decimal_places=2, read_only=True)
    amount_display = serializers.SerializerMethodField()
    due_date = serializers.DateField(source='invoice.due_date', read_only=True)
    due_date_display = serializers.SerializerMethodField()
    rule_name = serializers.CharField(source='reminder_rule.rule_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.SerializerMethodField()

    class Meta:
        model = Reminder
        fields = [
            "id",
            "scheduled_date",
            "invoice_number",
            "customer_name",
            "customer_email",
            "amount",
            "amount_display",
            "due_date",
            "due_date_display",
            "rule_name",
            "status",
            "status_display",
            "status_color",
        ]

    def get_customer_email(self, obj):
        # In a real app, you'd get this from a Customer model
        # For now, return a placeholder
        return f"{obj.invoice.customer_name.lower().replace(' ', '.')}@example.com"

    def get_amount_display(self, obj):
        amount = obj.invoice.total_amount
        return f"₹{amount:,.0f}"

    def get_due_date_display(self, obj):
        return obj.invoice.due_date.strftime("%d %b")

    def get_status_color(self, obj):
        colors = {
            "Pending": "#F59E0B",
            "Sent": "#10B981",
            "Cancelled": "#6B7280",
        }
        return colors.get(obj.status, "#6B7280")


class ReminderHistorySerializer(serializers.ModelSerializer):
    """Serializer for Sent Reminders History"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    amount = serializers.DecimalField(source='invoice.total_amount', max_digits=14, decimal_places=2, read_only=True)
    amount_display = serializers.SerializerMethodField()
    rule_name = serializers.CharField(source='reminder_rule.rule_name', read_only=True)
    sent_date_display = serializers.SerializerMethodField()

    class Meta:
        model = Reminder
        fields = [
            "id",
            "sent_at",
            "sent_date_display",
            "invoice_number",
            "customer_name",
            "amount",
            "amount_display",
            "rule_name",
            "status",
        ]

    def get_amount_display(self, obj):
        amount = obj.invoice.total_amount
        return f"₹{amount:,.0f}"

    def get_sent_date_display(self, obj):
        if obj.sent_at:
            return obj.sent_at.strftime("%d %b %Y")
        return None

