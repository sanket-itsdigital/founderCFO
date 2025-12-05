from rest_framework import serializers
from financial.models.account_payable.payment import PaymentMethodChoices


class RecordPaymentSerializer(serializers.Serializer):
    """Serializer for recording a payment"""
    bill_id = serializers.UUIDField()
    payment_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PaymentMethodChoices.choices)
    reference_number = serializers.CharField(max_length=255, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tds_deducted = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        required=False,
    )
    discount_taken = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class RecordPaymentResponseSerializer(serializers.Serializer):
    """Serializer for record payment response"""
    payment_id = serializers.UUIDField()
    bill_id = serializers.UUIDField()
    bill_number = serializers.CharField()
    payment_date = serializers.DateField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    payment_method = serializers.CharField()
    bill_status = serializers.CharField()
    bill_balance = serializers.FloatField()
    bill_balance_display = serializers.CharField()
    message = serializers.CharField()

