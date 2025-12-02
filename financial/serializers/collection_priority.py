from rest_framework import serializers


class CollectionPriorityCustomerSerializer(serializers.Serializer):
    """Serializer for individual customer in collection priority list"""
    customer_name = serializers.CharField()
    invoice_count = serializers.IntegerField()
    priority = serializers.CharField()  # Critical, High, Medium, Low
    priority_color = serializers.CharField()  # Color code for priority badge
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_display = serializers.CharField()  # Formatted as ₹XX.XXL
    days_overdue = serializers.IntegerField()  # Days overdue for oldest invoice
    recovery_percentage = serializers.FloatField()  # Estimated recovery percentage
    recommended_action = serializers.CharField()


class CollectionPrioritySummarySerializer(serializers.Serializer):
    """Serializer for collection priority summary metrics"""
    critical_count = serializers.IntegerField()
    high_priority_count = serializers.IntegerField()
    total_overdue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_overdue_display = serializers.CharField()  # Formatted as ₹XX.XXCr or ₹XX.XXL
    expected_recovery = serializers.DecimalField(max_digits=14, decimal_places=2)
    expected_recovery_display = serializers.CharField()  # Formatted as ₹XX.XXL
    total_customers = serializers.IntegerField()


class CollectionPrioritySerializer(serializers.Serializer):
    """Main serializer for Collection Priority dashboard"""
    summary = CollectionPrioritySummarySerializer()
    customers = CollectionPriorityCustomerSerializer(many=True)

