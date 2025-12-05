from rest_framework import serializers


class PaymentSchedulerBillSerializer(serializers.Serializer):
    """Serializer for bill in payment scheduler"""
    bill_id = serializers.UUIDField()
    bill_number = serializers.CharField()
    vendor_id = serializers.UUIDField(allow_null=True, required=False)
    vendor_name = serializers.CharField()
    due_date = serializers.DateField()
    due_date_display = serializers.CharField()
    days_overdue = serializers.IntegerField()
    days_until_due = serializers.IntegerField()
    days_display = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    discount_percentage = serializers.FloatField(allow_null=True, required=False)
    discount_amount = serializers.FloatField(allow_null=True, required=False)
    discount_display = serializers.CharField()
    status = serializers.CharField()
    is_selected = serializers.BooleanField(default=False)


class PaymentSchedulerGroupSerializer(serializers.Serializer):
    """Serializer for a group of bills (Overdue, Due This Week, etc.)"""
    group_name = serializers.CharField()
    bill_count = serializers.IntegerField()
    total_amount = serializers.FloatField()
    total_amount_display = serializers.CharField()
    potential_discount = serializers.FloatField(allow_null=True, required=False)
    potential_discount_display = serializers.CharField(allow_null=True, required=False)
    bills = PaymentSchedulerBillSerializer(many=True)


class PaymentSchedulerSummaryCardSerializer(serializers.Serializer):
    """Serializer for summary card"""
    title = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    bill_count = serializers.IntegerField()
    icon = serializers.CharField(required=False)


class PaymentSchedulerSerializer(serializers.Serializer):
    """Serializer for Payment Scheduler response"""
    summary_cards = PaymentSchedulerSummaryCardSerializer(many=True)
    overdue = PaymentSchedulerGroupSerializer()
    due_this_week = PaymentSchedulerGroupSerializer()
    due_next_week = PaymentSchedulerGroupSerializer()
    upcoming = PaymentSchedulerGroupSerializer()
    selected_for_payment = PaymentSchedulerGroupSerializer()

