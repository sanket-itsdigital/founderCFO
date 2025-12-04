from rest_framework import serializers


class InvoicedCollectedTrendSerializer(serializers.Serializer):
    """Serializer for Invoiced vs Collected Trend data"""
    month = serializers.CharField()
    invoiced = serializers.DecimalField(max_digits=14, decimal_places=2)
    invoiced_display = serializers.CharField()
    collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    collected_display = serializers.CharField()


class DSOTrendSerializer(serializers.Serializer):
    """Serializer for DSO Trend data"""
    month = serializers.CharField()
    dso = serializers.IntegerField()
    current_dso = serializers.IntegerField(read_only=True)


class OutstandingByCategorySerializer(serializers.Serializer):
    """Serializer for Outstanding by Category data"""
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    amount_display = serializers.CharField()
    color = serializers.CharField()


class TopOutstandingSerializer(serializers.Serializer):
    """Serializer for Top 5 Outstanding customers"""
    customer_name = serializers.CharField()
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_display = serializers.CharField()


class CollectionsByPaymentMethodSerializer(serializers.Serializer):
    """Serializer for Collections by Payment Method"""
    payment_method = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    amount_display = serializers.CharField()
    color = serializers.CharField()


class MonthlyCollectionRateSerializer(serializers.Serializer):
    """Serializer for Monthly Collection Rate"""
    month = serializers.CharField()
    collection_rate = serializers.FloatField()
    collection_rate_display = serializers.CharField()

