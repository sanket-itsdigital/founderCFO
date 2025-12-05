from rest_framework import serializers


class VendorBalanceVendorSerializer(serializers.Serializer):
    vendor_id = serializers.UUIDField(allow_null=True, required=False)
    vendor_name = serializers.CharField()
    outstanding = serializers.FloatField()
    outstanding_display = serializers.CharField()
    bill_count = serializers.IntegerField()
    oldest_bill_date = serializers.DateField(allow_null=True)
    oldest_bill_display = serializers.CharField()
    percentage_of_total = serializers.FloatField()


class VendorBalanceSummarySerializer(serializers.Serializer):
    total_outstanding = serializers.FloatField()
    total_outstanding_display = serializers.CharField()
    vendors = VendorBalanceVendorSerializer(many=True)
