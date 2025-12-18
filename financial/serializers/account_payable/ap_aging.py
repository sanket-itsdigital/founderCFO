from rest_framework import serializers


class APAgeingBucketSerializer(serializers.Serializer):
    """Serializer for individual ageing bucket"""

    label = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    percentage = serializers.FloatField()


class APAgeingOverviewSerializer(serializers.Serializer):
    """Serializer for AP Ageing Overview response"""

    ageing_buckets = APAgeingBucketSerializer(many=True)


class BillDetailSerializer(serializers.Serializer):
    """Serializer for individual bill details in expanded views"""

    bill_id = serializers.UUIDField()
    bill_number = serializers.CharField()
    vendor_name = serializers.CharField()
    due_date = serializers.DateField()
    category = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    status = serializers.CharField()


class VendorAgeingSerializer(serializers.Serializer):
    """Serializer for vendor-level ageing data"""

    vendor_id = serializers.UUIDField(allow_null=True)
    vendor_name = serializers.CharField()
    current_amount = serializers.FloatField()
    current_amount_display = serializers.CharField()
    overdue_1_30_amount = serializers.FloatField()
    overdue_1_30_amount_display = serializers.CharField()
    overdue_31_60_amount = serializers.FloatField()
    overdue_31_60_amount_display = serializers.CharField()
    overdue_61_90_amount = serializers.FloatField()
    overdue_61_90_amount_display = serializers.CharField()
    overdue_90_plus_amount = serializers.FloatField()
    overdue_90_plus_amount_display = serializers.CharField()
    total_amount = serializers.FloatField()
    total_amount_display = serializers.CharField()
    risk_level = serializers.CharField()
    bills = BillDetailSerializer(many=True, required=False)


class APAgeingByVendorSerializer(serializers.Serializer):
    """Serializer for AP Ageing By Vendor response"""

    vendors = VendorAgeingSerializer(many=True)
    totals = serializers.DictField()


class CategoryAgeingSerializer(serializers.Serializer):
    """Serializer for category-level ageing data"""

    category = serializers.CharField()
    current_amount = serializers.FloatField()
    current_amount_display = serializers.CharField()
    overdue_1_30_amount = serializers.FloatField()
    overdue_1_30_amount_display = serializers.CharField()
    overdue_31_60_amount = serializers.FloatField()
    overdue_31_60_amount_display = serializers.CharField()
    overdue_61_90_amount = serializers.FloatField()
    overdue_61_90_amount_display = serializers.CharField()
    overdue_90_plus_amount = serializers.FloatField()
    overdue_90_plus_amount_display = serializers.CharField()
    total_amount = serializers.FloatField()
    total_amount_display = serializers.CharField()
    bills = BillDetailSerializer(many=True, required=False)


class APAgeingByCategorySerializer(serializers.Serializer):
    """Serializer for AP Ageing By Category response"""

    categories = CategoryAgeingSerializer(many=True)
    totals = serializers.DictField()


class StatusAgeingSerializer(serializers.Serializer):
    """Serializer for status-level ageing data"""

    status = serializers.CharField()
    current_amount = serializers.FloatField()
    current_amount_display = serializers.CharField()
    overdue_1_30_amount = serializers.FloatField()
    overdue_1_30_amount_display = serializers.CharField()
    overdue_31_60_amount = serializers.FloatField()
    overdue_31_60_amount_display = serializers.CharField()
    overdue_61_90_amount = serializers.FloatField()
    overdue_61_90_amount_display = serializers.CharField()
    overdue_90_plus_amount = serializers.FloatField()
    overdue_90_plus_amount_display = serializers.CharField()
    total_amount = serializers.FloatField()
    total_amount_display = serializers.CharField()
    bills = BillDetailSerializer(many=True, required=False)


class APAgeingByStatusSerializer(serializers.Serializer):
    """Serializer for AP Ageing By Status response"""

    statuses = StatusAgeingSerializer(many=True)
    totals = serializers.DictField()


# Keep old serializer for backward compatibility
class APAgeingSummarySerializer(serializers.Serializer):
    """Serializer for AP Ageing Summary response (deprecated - use APAgeingOverviewSerializer)"""

    total_ap = serializers.FloatField()
    total_ap_display = serializers.CharField()
    overdue_percentage = serializers.FloatField()
    portfolio_health = serializers.CharField()
    ageing_buckets = APAgeingBucketSerializer(many=True)
