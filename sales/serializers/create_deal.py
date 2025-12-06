from decimal import Decimal

from rest_framework import serializers

from sales.enums import SalesProductChoices, SalesStageStatusChoices


class CreateDealSerializer(serializers.Serializer):
    """Serializer for creating a new deal"""
    account_name = serializers.CharField(max_length=255)
    deal_owner_id = serializers.UUIDField(allow_null=True, required=False)
    product = serializers.ChoiceField(choices=SalesProductChoices.choices, allow_null=True, required=False)
    expected_close_date = serializers.DateField()
    deal_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))
    monthly_recurring_revenue = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    stage = serializers.ChoiceField(choices=SalesStageStatusChoices.choices)
    probability = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        required=False,
    )
    status = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

