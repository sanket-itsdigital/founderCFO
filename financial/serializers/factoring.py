from rest_framework import serializers
from financial.models.factoring import FactoringRequest, FactoringRequestInvoice
from financial.models.account_receivable import Invoice


class FactoringRequestInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoices in factoring request"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer_name', read_only=True)
    amount = serializers.DecimalField(source='invoice.balance_amount', max_digits=14, decimal_places=2, read_only=True)
    amount_display = serializers.SerializerMethodField()
    due_date = serializers.DateField(source='invoice.due_date', read_only=True)
    due_status = serializers.SerializerMethodField()

    class Meta:
        model = FactoringRequestInvoice
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "customer_name",
            "amount",
            "amount_display",
            "due_date",
            "due_status",
        ]

    def get_amount_display(self, obj):
        return f"₹{obj.invoice.balance_amount:,.0f}"

    def get_due_status(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        days_diff = (obj.invoice.due_date - today).days
        
        if days_diff < 0:
            return f"{abs(days_diff)}d overdue"
        else:
            return f"{days_diff}d to due"


class FactoringRequestSerializer(serializers.ModelSerializer):
    """Serializer for FactoringRequest"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_receivables_display = serializers.SerializerMethodField()
    advance_amount_display = serializers.SerializerMethodField()
    factoring_fee_amount_display = serializers.SerializerMethodField()
    net_proceeds_display = serializers.SerializerMethodField()
    reserve_amount_display = serializers.SerializerMethodField()
    annualized_cost_display = serializers.SerializerMethodField()
    invoices = FactoringRequestInvoiceSerializer(many=True, read_only=True)
    invoice_count = serializers.SerializerMethodField()
    avg_days_to_due = serializers.SerializerMethodField()

    class Meta:
        model = FactoringRequest
        fields = [
            "id",
            "advance_rate",
            "factoring_fee",
            "processing_time_days",
            "status",
            "status_display",
            "total_receivables",
            "total_receivables_display",
            "advance_amount",
            "advance_amount_display",
            "factoring_fee_amount",
            "factoring_fee_amount_display",
            "net_proceeds",
            "net_proceeds_display",
            "reserve_amount",
            "reserve_amount_display",
            "annualized_cost",
            "annualized_cost_display",
            "invoice_count",
            "avg_days_to_due",
            "invoices",
            "created_at",
            "updated_at",
        ]

    def get_total_receivables_display(self, obj):
        return f"₹{obj.total_receivables:,.0f}"

    def get_advance_amount_display(self, obj):
        return f"₹{obj.advance_amount:,.0f}"

    def get_factoring_fee_amount_display(self, obj):
        return f"₹{obj.factoring_fee_amount:,.0f}"

    def get_net_proceeds_display(self, obj):
        return f"₹{obj.net_proceeds:,.0f}"

    def get_reserve_amount_display(self, obj):
        return f"₹{obj.reserve_amount:,.0f}"

    def get_annualized_cost_display(self, obj):
        return f"{obj.annualized_cost:.1f}%"

    def get_invoice_count(self, obj):
        return obj.invoices.count()

    def get_avg_days_to_due(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        invoices = obj.invoices.all()
        if not invoices.exists():
            return 0
        
        total_days = sum(
            (invoice.invoice.due_date - today).days 
            for invoice in invoices
        )
        return int(total_days / invoices.count()) if invoices.count() > 0 else 0


class FactoringRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating FactoringRequest"""
    invoice_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = FactoringRequest
        fields = [
            "advance_rate",
            "factoring_fee",
            "processing_time_days",
            "invoice_ids",
        ]

