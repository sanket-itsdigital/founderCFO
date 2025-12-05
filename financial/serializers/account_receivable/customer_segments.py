from rest_framework import serializers


class CustomerSegmentDetailSerializer(serializers.Serializer):
    """Serializer for individual customer in a segment"""

    customer_name = serializers.CharField()
    invoice_count = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_revenue_display = serializers.CharField()
    avg_payment_days = serializers.IntegerField()
    risk_level = serializers.CharField()


class SegmentSummarySerializer(serializers.Serializer):
    """Serializer for segment summary card"""

    segment_name = serializers.CharField()
    customer_count = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_revenue_display = serializers.CharField()
    avg_payment_days = serializers.IntegerField()
    risk_level = serializers.CharField()
    characteristics = serializers.ListField(child=serializers.CharField())
    customers = CustomerSegmentDetailSerializer(many=True)


class SegmentDetailSerializer(serializers.Serializer):
    """Serializer for Segment Details table row"""

    segment = serializers.CharField()
    customers = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_revenue_display = serializers.CharField()
    avg_payment_days = serializers.IntegerField()
    risk_level = serializers.CharField()
    characteristics = serializers.ListField(child=serializers.CharField())


class CustomerSegmentsSerializer(serializers.Serializer):
    """Serializer for Customer Segments response"""

    segments = SegmentSummarySerializer(many=True)
    segment_details = SegmentDetailSerializer(many=True)
    customer_distribution = serializers.DictField()
    revenue_by_segment = serializers.DictField()
