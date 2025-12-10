from decimal import Decimal
from rest_framework import serializers


class CustomerRevenueSerializer(serializers.Serializer):
    """Serializer for Revenue by Customer"""

    customer_name = serializers.CharField()
    invoices_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_value = serializers.DecimalField(max_digits=14, decimal_places=2)


class ProductRevenueSerializer(serializers.Serializer):
    """Serializer for Revenue by Product"""

    product_name = serializers.CharField()
    invoices_count = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class SalespersonRevenueSerializer(serializers.Serializer):
    """Serializer for Revenue by Salesperson"""

    salesperson = serializers.CharField()
    invoices_count = serializers.IntegerField()
    customers_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_deal = serializers.DecimalField(max_digits=14, decimal_places=2)
    share = serializers.DecimalField(max_digits=5, decimal_places=2)


class ServiceRevenueSerializer(serializers.Serializer):
    """Serializer for Revenue by Service/Category"""

    service_type = serializers.CharField()
    invoices_count = serializers.IntegerField()
    customers_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    share = serializers.DecimalField(max_digits=5, decimal_places=2)
