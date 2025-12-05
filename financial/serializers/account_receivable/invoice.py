from rest_framework import serializers
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice list and detail views"""
    balance_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True
    )
    balance_amount_display = serializers.SerializerMethodField()
    total_amount_display = serializers.SerializerMethodField()
    paid_amount_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    payment_terms_display = serializers.CharField(source='get_payment_terms_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "company",
            "invoice_number",
            "customer_name",
            "invoice_date",
            "payment_terms",
            "payment_terms_display",
            "due_date",
            "subtotal_amount",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "total_amount_display",
            "paid_amount",
            "paid_amount_display",
            "balance_amount",
            "balance_amount_display",
            "category",
            "category_display",
            "status",
            "status_display",
            "sales_order_reference",
            "notes",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "balance_amount",
            "balance_amount_display",
            "total_amount_display",
            "paid_amount_display",
            "status_display",
            "is_overdue",
            "payment_terms_display",
            "category_display",
            "created_at",
            "updated_at",
        ]

    def get_balance_amount_display(self, obj):
        """Format balance amount in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        balance = obj.balance_amount
        if balance == 0:
            return "₹0.00L"
        lakhs = balance / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_total_amount_display(self, obj):
        """Format total amount in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        if obj.total_amount == 0:
            return "₹0.00L"
        lakhs = obj.total_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_paid_amount_display(self, obj):
        """Format paid amount in lakhs (₹XX.XXL)"""
        from decimal import Decimal
        if obj.paid_amount == 0:
            return "₹0.00L"
        lakhs = obj.paid_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def validate(self, data):
        """Validate invoice data"""
        # Ensure total_amount is calculated if subtotal is provided
        if 'subtotal_amount' in data and 'total_amount' not in data:
            subtotal = data.get('subtotal_amount', 0)
            tax = data.get('tax_amount', 0)
            discount = data.get('discount_amount', 0)
            data['total_amount'] = subtotal + tax - discount
        
        # Ensure paid_amount doesn't exceed total_amount
        if 'paid_amount' in data and 'total_amount' in data:
            if data['paid_amount'] > data['total_amount']:
                raise serializers.ValidationError({
                    "paid_amount": "Paid amount cannot exceed total amount"
                })
        
        return data


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating invoices - company is set automatically"""
    
    class Meta:
        model = Invoice
        fields = [
            "invoice_number",
            "customer_name",
            "invoice_date",
            "payment_terms",
            "due_date",
            "subtotal_amount",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "paid_amount",
            "category",
            "status",
            "sales_order_reference",
            "notes",
        ]

    def validate(self, data):
        """Validate invoice data"""
        # Ensure total_amount is calculated if subtotal is provided
        if 'subtotal_amount' in data and 'total_amount' not in data:
            subtotal = data.get('subtotal_amount', 0)
            tax = data.get('tax_amount', 0)
            discount = data.get('discount_amount', 0)
            data['total_amount'] = subtotal + tax - discount
        
        # Ensure paid_amount doesn't exceed total_amount
        if 'paid_amount' in data and 'total_amount' in data:
            if data['paid_amount'] > data['total_amount']:
                raise serializers.ValidationError({
                    "paid_amount": "Paid amount cannot exceed total amount"
                })
        
        return data

