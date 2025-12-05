from rest_framework import serializers


class InvoiceStatusSerializer(serializers.Serializer):
    """Serializer for invoice status counts"""
    total = serializers.IntegerField()
    paid = serializers.IntegerField()
    pending = serializers.IntegerField()
    overdue = serializers.IntegerField()


class KPISerializer(serializers.Serializer):
    """Serializer for Key Performance Indicators"""
    total_receivables = serializers.FloatField()
    total_receivables_display = serializers.CharField()
    total_receivables_trend = serializers.CharField(required=False, allow_null=True)
    dso = serializers.IntegerField()
    collection_efficiency = serializers.FloatField()
    overdue_ar = serializers.FloatField()
    overdue_ar_percentage = serializers.FloatField()
    overdue_ar_display = serializers.CharField()
    avg_days_delinquent = serializers.IntegerField()
    this_month_collections = serializers.FloatField()
    this_month_collections_display = serializers.CharField()
    this_month_collections_trend = serializers.CharField(required=False, allow_null=True)
    invoice_status = InvoiceStatusSerializer()


class ARHealthMetricSerializer(serializers.Serializer):
    """Serializer for AR Health metrics"""
    dso = serializers.IntegerField()
    dso_target = serializers.IntegerField()
    dso_status = serializers.CharField()  # High, Normal, Low
    collection_efficiency = serializers.FloatField()
    collection_efficiency_status = serializers.CharField()  # High, Normal, Low
    overdue_amount = serializers.FloatField()
    overdue_amount_display = serializers.CharField()
    overdue_percentage = serializers.FloatField()
    top_customer_concentration = serializers.FloatField()
    top_customer_name = serializers.CharField()
    top_customer_status = serializers.CharField()  # Diversified, Concentrated, High Risk


class ARHealthStatusSerializer(serializers.Serializer):
    """Serializer for AR Health Status"""
    status = serializers.CharField()  # Healthy, Needs Attention, Critical
    total_receivables = serializers.FloatField()
    total_receivables_display = serializers.CharField()
    metrics = ARHealthMetricSerializer()


class AgeingBucketSerializer(serializers.Serializer):
    """Serializer for ageing bucket"""
    label = serializers.CharField()
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    percentage = serializers.FloatField()
    color = serializers.CharField()


class PriorityActionSerializer(serializers.Serializer):
    """Serializer for priority actions"""
    critical_count = serializers.IntegerField()
    due_this_week_count = serializers.IntegerField()
    collected_this_month = serializers.FloatField()
    collected_this_month_display = serializers.CharField()


class TopCustomerSerializer(serializers.Serializer):
    """Serializer for top customer"""
    customer_name = serializers.CharField()
    invoice_count = serializers.IntegerField()
    outstanding = serializers.FloatField()
    outstanding_display = serializers.CharField()
    percentage = serializers.FloatField()


class CollectionTrendSerializer(serializers.Serializer):
    """Serializer for collection trend data point"""
    month = serializers.CharField()
    collected = serializers.FloatField()
    collected_display = serializers.CharField()
    invoiced = serializers.FloatField()
    invoiced_display = serializers.CharField()


class ARDashboardSerializer(serializers.Serializer):
    """Serializer for AR Dashboard response"""
    kpis = KPISerializer()
    ar_health_status = ARHealthStatusSerializer()
    ageing_distribution = serializers.ListField(child=AgeingBucketSerializer())
    priority_actions = PriorityActionSerializer()
    top_customers = serializers.ListField(child=TopCustomerSerializer())
    collection_trend = serializers.ListField(child=CollectionTrendSerializer())

