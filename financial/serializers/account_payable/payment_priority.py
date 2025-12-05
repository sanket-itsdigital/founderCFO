from rest_framework import serializers


class PaymentPriorityBillSerializer(serializers.Serializer):
    """Serializer for individual bill in payment priority queue"""
    bill_id = serializers.UUIDField()
    bill_number = serializers.CharField()
    vendor_id = serializers.UUIDField(allow_null=True, required=False)
    vendor_name = serializers.CharField()
    due_date = serializers.DateField()
    due_date_display = serializers.CharField()
    days_overdue = serializers.IntegerField()
    days_display = serializers.CharField()
    amount_due = serializers.FloatField()
    amount_due_display = serializers.CharField()
    discount_percentage = serializers.FloatField(allow_null=True, required=False)
    discount_display = serializers.CharField()
    priority = serializers.CharField()
    priority_color = serializers.CharField()


class PaymentPriorityQueueSerializer(serializers.Serializer):
    """Serializer for Payment Priority Queue response"""
    bills = PaymentPriorityBillSerializer(many=True)
    summary = serializers.DictField()

