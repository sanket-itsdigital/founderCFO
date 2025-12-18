from decimal import Decimal
from rest_framework import serializers
from expense.models.bills import Bill
from financial.models.account_payable.vendor import Vendor
from financial.enums import BillsStatusChoices, InvoicesPaymentTerms


class BillSerializer(serializers.ModelSerializer):
    """Serializer for Bill model - List and Detail views"""

    vendor_id = serializers.UUIDField(
        source="vendor.id", read_only=True, allow_null=True
    )
    vendor_name = serializers.CharField(source="get_vendor_name", read_only=True)
    amount = serializers.DecimalField(
        source="total", max_digits=14, decimal_places=2, read_only=True
    )
    amount_display = serializers.SerializerMethodField()
    paid_amount_display = serializers.SerializerMethodField()
    balance_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    balance_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    total_gst = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "bill_date",
            "due_date",
            "vendor_id",
            "vendor_name",
            "vendor_gstin",
            "vendor_pan",
            "item_name",
            "hsn_sac",
            "category",
            "place_of_supply",
            "subtotal",
            "cgst_percentage",
            "cgst_amount",
            "sgst_percentage",
            "sgst_amount",
            "igst_percentage",
            "igst_amount",
            "total_gst",
            "tds_section",
            "tds_percentage",
            "tds_amount",
            "total",
            "amount",
            "amount_display",
            "paid_amount",
            "paid_amount_display",
            "balance_amount",
            "balance_display",
            "payment_terms",
            "status",
            "status_display",
            "department",
            "branch",
            "notes",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "tds_amount",
            "total",
            "created_at",
            "updated_at",
        ]

    def get_amount_display(self, obj):
        """Format amount for display"""
        if obj.total == 0:
            return "₹0"
        if obj.total < 1000:
            return f"₹{obj.total:,.2f}"
        elif obj.total < 100000:
            return f"₹{obj.total / 1000:.2f}K"
        else:
            return f"₹{obj.total / 100000:.2f}L"

    def get_paid_amount_display(self, obj):
        """Format paid amount for display"""
        if obj.paid_amount == 0:
            return "₹0"
        if obj.paid_amount < 1000:
            return f"₹{obj.paid_amount:,.2f}"
        elif obj.paid_amount < 100000:
            return f"₹{obj.paid_amount / 1000:.2f}K"
        else:
            return f"₹{obj.paid_amount / 100000:.2f}L"

    def get_balance_display(self, obj):
        """Format balance amount for display"""
        balance = obj.balance_amount
        if balance == 0:
            return "₹0"
        if balance < 1000:
            return f"₹{balance:,.2f}"
        elif balance < 100000:
            return f"₹{balance / 1000:.2f}K"
        else:
            return f"₹{balance / 100000:.2f}L"

    def get_total_gst(self, obj):
        """Calculate total GST (CGST + SGST + IGST)"""
        return obj.cgst_amount + obj.sgst_amount + obj.igst_amount


class BillCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Bill - handles vendor creation/update"""

    # Vendor fields (for creating/updating vendor)
    vendor_name = serializers.CharField(write_only=True, required=True)
    vendor_gstin = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    vendor_pan = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    vendor_mobile = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    vendor_email = serializers.EmailField(
        write_only=True, required=False, allow_blank=True
    )
    vendor_address = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    is_vendor_out_of_india = serializers.BooleanField(write_only=True, default=False)

    # Basic Info
    bill_date = serializers.DateField(required=True)
    invoice_date = serializers.DateField(
        required=False, allow_null=True
    )  # Not in model, but accepted
    bill_number = serializers.CharField(required=True)

    # Service/Goods
    item_name = serializers.CharField(required=False, allow_blank=True)
    hsn_sac = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=True)
    place_of_supply = serializers.CharField(required=False, allow_blank=True)
    supply_type = serializers.CharField(
        required=False, allow_blank=True
    )  # Not in model, but accepted

    # Tax & TDS
    subtotal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=True, min_value=Decimal("0.00")
    )
    cgst_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    sgst_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    igst_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    tds_section = serializers.CharField(required=False, allow_blank=True)
    tds_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )

    # Payment
    payment_terms = serializers.ChoiceField(
        choices=InvoicesPaymentTerms.choices, required=False, allow_blank=True
    )
    due_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=BillsStatusChoices.choices,
        required=False,
        default=BillsStatusChoices.PENDING,
    )
    department = serializers.CharField(required=False, allow_blank=True)
    cost_center = serializers.CharField(
        required=False, allow_blank=True
    )  # Not in model, but accepted
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Bill
        fields = [
            # Basic Info
            "bill_number",
            "bill_date",
            "invoice_date",
            "due_date",
            # Vendor Info
            "vendor_name",
            "vendor_gstin",
            "vendor_pan",
            "vendor_mobile",
            "vendor_email",
            "vendor_address",
            "is_vendor_out_of_india",
            # Service/Goods
            "item_name",
            "hsn_sac",
            "category",
            "place_of_supply",
            "supply_type",
            # Tax & TDS
            "subtotal",
            "cgst_percentage",
            "sgst_percentage",
            "igst_percentage",
            "tds_section",
            "tds_percentage",
            # Payment
            "payment_terms",
            "status",
            "department",
            "cost_center",
            "notes",
        ]

    def validate(self, attrs):
        """Validate bill data"""
        # Validate that at least one GST type is provided if subtotal > 0
        subtotal = attrs.get("subtotal", Decimal("0.00"))
        if subtotal > 0:
            cgst = attrs.get("cgst_percentage", Decimal("0.00"))
            sgst = attrs.get("sgst_percentage", Decimal("0.00"))
            igst = attrs.get("igst_percentage", Decimal("0.00"))

            # If IGST is provided, CGST and SGST should be 0
            if igst > 0 and (cgst > 0 or sgst > 0):
                raise serializers.ValidationError(
                    "IGST and CGST/SGST cannot both be provided. Use IGST for inter-state transactions."
                )

        return attrs

    def create(self, validated_data):
        """Create bill with vendor handling"""
        # Extract vendor data
        vendor_name = validated_data.pop("vendor_name")
        vendor_gstin = validated_data.pop("vendor_gstin", "")
        vendor_pan = validated_data.pop("vendor_pan", "")
        vendor_mobile = validated_data.pop("vendor_mobile", "")
        vendor_email = validated_data.pop("vendor_email", "")
        vendor_address = validated_data.pop("vendor_address", "")
        is_vendor_out_of_india = validated_data.pop("is_vendor_out_of_india", False)

        # Remove fields not in model
        validated_data.pop("invoice_date", None)
        validated_data.pop("supply_type", None)
        validated_data.pop("cost_center", None)

        # Get company from context
        company = self.context["company"]
        user = self.context.get("user")

        # Get or create vendor
        vendor, created = Vendor.objects.get_or_create(
            company=company,
            name=vendor_name,
            defaults={
                "gstin": vendor_gstin or None,
                "pan": vendor_pan or None,
                "phone": vendor_mobile or None,
                "email": vendor_email or None,
                "address": vendor_address or None,
                "created_by": user,
                "updated_by": user,
            },
        )

        # Update vendor if it already exists and new data is provided
        if not created:
            updated = False
            if vendor_gstin and not vendor.gstin:
                vendor.gstin = vendor_gstin
                updated = True
            if vendor_pan and not vendor.pan:
                vendor.pan = vendor_pan
                updated = True
            if vendor_mobile and not vendor.phone:
                vendor.phone = vendor_mobile
                updated = True
            if vendor_email and not vendor.email:
                vendor.email = vendor_email
                updated = True
            if vendor_address and not vendor.address:
                vendor.address = vendor_address
                updated = True
            if updated and user:
                vendor.updated_by = user
                vendor.save()

        # Create bill
        validated_data["vendor"] = vendor
        validated_data["vendor_name"] = vendor_name
        validated_data["vendor_gstin"] = vendor_gstin or vendor.gstin or ""
        validated_data["vendor_pan"] = vendor_pan or vendor.pan or ""
        validated_data["company"] = company

        # Set created_by and updated_by if user is available
        if user:
            validated_data["created_by"] = user
            validated_data["updated_by"] = user

        bill = Bill.objects.create(**validated_data)
        return bill
