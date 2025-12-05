from rest_framework import serializers
from financial.models.account_payable.bills import Bill
from financial.models.account_payable.vendor import Vendor
from financial.enums import BillsStatusChoices


class BillSerializer(serializers.ModelSerializer):
    """Serializer for Bill list and detail views"""
    balance_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    vendor_name = serializers.CharField(read_only=True, source="get_vendor_name")
    vendor_id = serializers.UUIDField(source="vendor.id", read_only=True, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    
    # Format amounts for display
    amount_display = serializers.SerializerMethodField()
    balance_display = serializers.SerializerMethodField()
    paid_amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "vendor",
            "vendor_id",
            "vendor_name",
            "bill_date",
            "due_date",
            "amount",
            "amount_display",
            "paid_amount",
            "paid_amount_display",
            "balance_amount",
            "balance_display",
            "status",
            "status_display",
            "category",
            "notes",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "balance_amount"]

    def get_amount_display(self, obj):
        """Format amount as ₹XX.XXL"""
        if obj.amount == 0:
            return "₹0.00L"
        from decimal import Decimal
        lakhs = obj.amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_balance_display(self, obj):
        """Format balance as ₹XX.XXL"""
        balance = obj.balance_amount
        if balance == 0:
            return "₹0.00L"
        from decimal import Decimal
        lakhs = balance / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get_paid_amount_display(self, obj):
        """Format paid amount as ₹XX.XXL"""
        if obj.paid_amount == 0:
            return "₹0.00L"
        from decimal import Decimal
        lakhs = obj.paid_amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"


class BillCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bills"""
    vendor_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Vendor name (used if vendor FK not provided)",
    )

    class Meta:
        model = Bill
        fields = [
            "bill_number",
            "vendor",
            "vendor_name",
            "bill_date",
            "due_date",
            "amount",
            "paid_amount",
            "status",
            "category",
            "notes",
        ]

    def validate(self, data):
        """Validate bill data"""
        # Ensure either vendor FK or vendor_name is provided
        vendor = data.get("vendor")
        vendor_name = data.get("vendor_name", "")
        
        if not vendor and not vendor_name:
            raise serializers.ValidationError({
                "vendor": "Either vendor or vendor_name must be provided."
            })
        
        # Validate dates
        bill_date = data.get("bill_date")
        due_date = data.get("due_date")
        
        if bill_date and due_date and due_date < bill_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be before bill date."
            })
        
        # Validate amounts
        amount = data.get("amount", 0)
        paid_amount = data.get("paid_amount", 0)
        
        if paid_amount > amount:
            raise serializers.ValidationError({
                "paid_amount": "Paid amount cannot exceed bill amount."
            })
        
        return data

    def create(self, validated_data):
        """Create bill with vendor name sync"""
        vendor = validated_data.get("vendor")
        vendor_name = validated_data.get("vendor_name", "")
        
        # If vendor FK is provided, use its name
        if vendor:
            validated_data["vendor_name"] = vendor.name
        elif vendor_name:
            # If only vendor_name provided, try to find or create vendor
            company = validated_data.get("company")
            if company:
                vendor, created = Vendor.objects.get_or_create(
                    company=company,
                    name=vendor_name,
                    defaults={
                        "created_by": self.context["request"].user if self.context["request"].user.is_authenticated else None,
                        "updated_by": self.context["request"].user if self.context["request"].user.is_authenticated else None,
                    }
                )
                validated_data["vendor"] = vendor
                validated_data["vendor_name"] = vendor.name
        
        return super().create(validated_data)


class BillUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating bills"""
    vendor_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Vendor name (used if vendor FK not provided)",
    )

    class Meta:
        model = Bill
        fields = [
            "bill_number",
            "vendor",
            "vendor_name",
            "bill_date",
            "due_date",
            "amount",
            "paid_amount",
            "status",
            "category",
            "notes",
        ]

    def validate(self, data):
        """Validate bill data"""
        # Similar validation as create
        vendor = data.get("vendor")
        vendor_name = data.get("vendor_name")
        
        # If updating, get existing values
        if self.instance:
            if vendor is None and "vendor" not in data:
                vendor = self.instance.vendor
            if vendor_name is None and "vendor_name" not in data:
                vendor_name = self.instance.vendor_name
        
        if not vendor and not vendor_name:
            raise serializers.ValidationError({
                "vendor": "Either vendor or vendor_name must be provided."
            })
        
        # Validate dates
        bill_date = data.get("bill_date", self.instance.bill_date if self.instance else None)
        due_date = data.get("due_date", self.instance.due_date if self.instance else None)
        
        if bill_date and due_date and due_date < bill_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be before bill date."
            })
        
        # Validate amounts
        amount = data.get("amount", self.instance.amount if self.instance else 0)
        paid_amount = data.get("paid_amount", self.instance.paid_amount if self.instance else 0)
        
        if paid_amount > amount:
            raise serializers.ValidationError({
                "paid_amount": "Paid amount cannot exceed bill amount."
            })
        
        return data

    def update(self, instance, validated_data):
        """Update bill with vendor name sync"""
        vendor = validated_data.get("vendor")
        vendor_name = validated_data.get("vendor_name")
        
        # If vendor FK is provided, use its name
        if vendor:
            validated_data["vendor_name"] = vendor.name
        elif vendor_name and not vendor:
            # If only vendor_name provided, try to find or create vendor
            company = instance.company
            if company:
                vendor, created = Vendor.objects.get_or_create(
                    company=company,
                    name=vendor_name,
                    defaults={
                        "created_by": self.context["request"].user if self.context["request"].user.is_authenticated else None,
                        "updated_by": self.context["request"].user if self.context["request"].user.is_authenticated else None,
                    }
                )
                validated_data["vendor"] = vendor
                validated_data["vendor_name"] = vendor.name
        
        return super().update(instance, validated_data)

