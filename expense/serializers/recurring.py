from decimal import Decimal
from rest_framework import serializers
from expense.models.recurring import (
    RecurringExpense,
    RecurringExpenseFrequencyChoices,
    RecurringExpenseStatusChoices,
)
from financial.models.account_payable.vendor import Vendor


class RecurringExpenseSerializer(serializers.ModelSerializer):
    """Serializer for RecurringExpense (list/detail view)"""

    vendor_id = serializers.UUIDField(
        source="vendor.id", read_only=True, allow_null=True
    )
    vendor_name_display = serializers.CharField(
        source="get_vendor_display", read_only=True
    )
    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    next_due_date = serializers.SerializerMethodField()
    next_due_date_display = serializers.SerializerMethodField()
    is_due_soon = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    total_amount_display = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()
    tax_display = serializers.SerializerMethodField()

    class Meta:
        model = RecurringExpense
        fields = [
            "id",
            "name",
            "vendor_id",
            "vendor_name",
            "vendor_name_display",
            "description",
            "category",
            "sub_category",
            "amount",
            "amount_display",
            "tax",
            "tax_display",
            "total_amount",
            "total_amount_display",
            "frequency",
            "frequency_display",
            "start_date",
            "end_date",
            "contract_reference",
            "auto_generate_expenses",
            "days_before_due_to_generate",
            "renewal_reminder_days",
            "status",
            "status_display",
            "notes",
            "next_due_date",
            "next_due_date_display",
            "is_due_soon",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores with Indian numbering"""
        if amount == 0:
            return "₹0"
        if amount < 1000:
            return f"₹{amount:,.2f}"
        elif amount < 100000:
            return f"₹{amount / 1000:.2f}K"
        elif amount < 10000000:  # Less than 1 crore
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:  # 1 crore or more
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    def get_next_due_date(self, obj):
        """Get next due date"""
        next_due = obj.calculate_next_due_date()
        return next_due.isoformat() if next_due else None

    def get_next_due_date_display(self, obj):
        """Get formatted next due date"""
        next_due = obj.calculate_next_due_date()
        if not next_due:
            return "N/A"
        return next_due.strftime("%d %b %Y")

    def get_is_due_soon(self, obj):
        """Check if expense is due soon (within 7 days)"""
        return obj.is_due_soon(days=7)

    def get_is_overdue(self, obj):
        """Check if expense is overdue"""
        return obj.is_overdue()

    def get_total_amount(self, obj):
        """Get total amount including tax"""
        return float(obj.get_total_amount())

    def get_total_amount_display(self, obj):
        """Get formatted total amount"""
        return self._format_amount(obj.get_total_amount())

    def get_amount_display(self, obj):
        """Get formatted amount"""
        return self._format_amount(obj.amount)

    def get_tax_display(self, obj):
        """Get formatted tax"""
        return self._format_amount(obj.tax)


class RecurringExpenseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating RecurringExpense"""

    vendor_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    vendor_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = RecurringExpense
        fields = [
            "name",
            "vendor_id",
            "vendor_name",
            "description",
            "category",
            "sub_category",
            "amount",
            "tax",
            "frequency",
            "start_date",
            "end_date",
            "contract_reference",
            "auto_generate_expenses",
            "days_before_due_to_generate",
            "renewal_reminder_days",
            "status",
            "notes",
        ]

    def validate(self, attrs):
        """Validate the data"""
        # Ensure either vendor_id or vendor_name is provided
        vendor_id = attrs.get("vendor_id")
        vendor_name = attrs.get("vendor_name", "").strip()

        if not vendor_id and not vendor_name:
            raise serializers.ValidationError(
                {"vendor": "Either vendor_id or vendor_name must be provided"}
            )

        # Validate frequency
        frequency = attrs.get("frequency")
        if frequency and frequency not in RecurringExpenseFrequencyChoices.values:
            raise serializers.ValidationError(
                {
                    "frequency": f"Frequency must be one of: {', '.join(RecurringExpenseFrequencyChoices.values)}"
                }
            )

        # Validate dates
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date"}
            )

        return attrs

    def create(self, validated_data):
        """Create a new recurring expense"""
        vendor_id = validated_data.pop("vendor_id", None)
        vendor_name = validated_data.pop("vendor_name", "").strip()
        company = self.context["request"].user.company

        # Handle vendor
        vendor = None
        if vendor_id:
            try:
                vendor = Vendor.objects.get(id=vendor_id, company=company)
            except Vendor.DoesNotExist:
                raise serializers.ValidationError({"vendor_id": "Vendor not found"})
        elif vendor_name:
            # Try to find existing vendor or create new one
            vendor, _ = Vendor.objects.get_or_create(
                name=vendor_name,
                company=company,
                defaults={"name": vendor_name},
            )

        validated_data["vendor"] = vendor
        validated_data["vendor_name"] = vendor_name if not vendor else ""
        validated_data["company"] = company

        return RecurringExpense.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing recurring expense"""
        vendor_id = validated_data.pop("vendor_id", None)
        vendor_name = validated_data.pop("vendor_name", None)
        company = self.context["request"].user.company

        # Handle vendor update
        if vendor_id is not None:
            if vendor_id:
                try:
                    vendor = Vendor.objects.get(id=vendor_id, company=company)
                    instance.vendor = vendor
                    instance.vendor_name = ""
                except Vendor.DoesNotExist:
                    raise serializers.ValidationError({"vendor_id": "Vendor not found"})
            else:
                instance.vendor = None
                instance.vendor_name = vendor_name or ""

        if vendor_name is not None and not instance.vendor:
            instance.vendor_name = vendor_name

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecurringExpenseFrequencyChoicesSerializer(serializers.Serializer):
    """Serializer for frequency choices (for dropdown)"""

    value = serializers.CharField()
    label = serializers.CharField()


class RecurringExpenseStatusChoicesSerializer(serializers.Serializer):
    """Serializer for status choices (for dropdown)"""

    value = serializers.CharField()
    label = serializers.CharField()
