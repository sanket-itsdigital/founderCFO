from decimal import Decimal

from rest_framework import serializers

from accounts.models import Company
from accounts.serializers.auth import UserProfileListSerializer, UserProfileSerializer


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for creating a Company linked to the request user as owner."""

    owner = UserProfileListSerializer(read_only=True)
    total_shareholders_funds = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )
    capital_utilization_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    available_capital = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "GST_number",
            "address",
            "no_of_employees",
            "nature_of_business",
            "owner",
            # Capital Structure Fields
            "face_value_per_share",
            "authorized_capital_amount",
            "authorized_capital_shares",
            "issued_capital_amount",
            "issued_capital_shares",
            "paid_up_capital_amount",
            "paid_up_capital_shares",
            "securities_premium",
            # ESOP Pool Fields
            "esop_pool_size",
            "esop_pool_percentage",
            "esop_pool_notes",
            # Computed Fields
            "total_shareholders_funds",
            "capital_utilization_percentage",
            "available_capital",
        )
        read_only_fields = (
            "id",
            "owner",
            "total_shareholders_funds",
            "capital_utilization_percentage",
            "available_capital",
        )

    def create(self, validated_data):
        # owner should be provided by the view via serializer.save(owner=...)
        # If owner is already in validated_data (from view's save call), use it
        # Otherwise, try to get from request context as fallback
        owner = validated_data.pop("owner", None)

        if owner is None:
            request = self.context.get("request")
            if request is None or not hasattr(request, "user"):
                raise serializers.ValidationError(
                    "Request user is required to create a company."
                )
            owner = request.user

        # Set created_by and updated_by from the owner/user
        # These fields are required by BaseModel validation
        return Company.objects.create(
            owner=owner,
            created_by=owner,
            updated_by=owner,
            **validated_data
        )

    def validate(self, attrs):
        """Validate capital structure relationships and auto-calculate amounts/shares/price."""
        validated_data = (
            super().validate(attrs) if hasattr(super(), "validate") else attrs
        )

        # Get current values (for updates) or new values (for creates)
        instance = getattr(self, "instance", None)

        # Get face_value_per_share
        face_value = validated_data.get("face_value_per_share")
        if face_value is None and instance:
            face_value = instance.face_value_per_share

        authorized_amount = validated_data.get("authorized_capital_amount")
        if authorized_amount is None and instance:
            authorized_amount = instance.authorized_capital_amount

        issued_amount = validated_data.get("issued_capital_amount")
        if issued_amount is None and instance:
            issued_amount = instance.issued_capital_amount

        paid_up_amount = validated_data.get("paid_up_capital_amount")
        if paid_up_amount is None and instance:
            paid_up_amount = instance.paid_up_capital_amount

        authorized_shares = validated_data.get("authorized_capital_shares")
        if authorized_shares is None and instance:
            authorized_shares = instance.authorized_capital_shares

        issued_shares = validated_data.get("issued_capital_shares")
        if issued_shares is None and instance:
            issued_shares = instance.issued_capital_shares

        paid_up_shares = validated_data.get("paid_up_capital_shares")
        if paid_up_shares is None and instance:
            paid_up_shares = instance.paid_up_capital_shares

        # Auto-calculation logic - Bidirectional for each capital type
        # Step 1: Determine effective face_value_per_share
        effective_face_value = face_value

        # Priority 1: If face_value_per_share is explicitly provided
        if (
            "face_value_per_share" in validated_data
            and validated_data["face_value_per_share"]
        ):
            effective_face_value = validated_data["face_value_per_share"]

        # Priority 2: Calculate face_value_per_share from any available amount/shares pair
        if not effective_face_value or effective_face_value == 0:
            # Try authorized capital first (highest priority)
            auth_amount = validated_data.get(
                "authorized_capital_amount", authorized_amount
            )
            auth_shares = validated_data.get(
                "authorized_capital_shares", authorized_shares
            )
            if auth_amount and auth_shares and auth_shares > 0:
                effective_face_value = auth_amount / Decimal(auth_shares)
                if "face_value_per_share" not in validated_data:
                    validated_data["face_value_per_share"] = (
                        effective_face_value.quantize(Decimal("0.0001"))
                    )

            # Try issued capital (fallback)
            if not effective_face_value or effective_face_value == 0:
                issued_amt = validated_data.get("issued_capital_amount", issued_amount)
                issued_shrs = validated_data.get("issued_capital_shares", issued_shares)
                if issued_amt and issued_shrs and issued_shrs > 0:
                    effective_face_value = issued_amt / Decimal(issued_shrs)
                    if "face_value_per_share" not in validated_data:
                        validated_data["face_value_per_share"] = (
                            effective_face_value.quantize(Decimal("0.0001"))
                        )

            # Try paid-up capital (fallback)
            if not effective_face_value or effective_face_value == 0:
                paid_amt = validated_data.get("paid_up_capital_amount", paid_up_amount)
                paid_shrs = validated_data.get("paid_up_capital_shares", paid_up_shares)
                if paid_amt and paid_shrs and paid_shrs > 0:
                    effective_face_value = paid_amt / Decimal(paid_shrs)
                    if "face_value_per_share" not in validated_data:
                        validated_data["face_value_per_share"] = (
                            effective_face_value.quantize(Decimal("0.0001"))
                        )

        # Step 2: Calculate missing fields for each capital type using effective_face_value
        if effective_face_value and effective_face_value > 0:
            # AUTHORIZED CAPITAL - Calculate missing field (amount or shares)
            auth_amount_provided = "authorized_capital_amount" in validated_data
            auth_shares_provided = "authorized_capital_shares" in validated_data
            auth_amount_val = validated_data.get(
                "authorized_capital_amount", authorized_amount
            )
            auth_shares_val = validated_data.get(
                "authorized_capital_shares", authorized_shares
            )

            if auth_amount_provided and auth_amount_val and not auth_shares_provided:
                # Amount provided, calculate shares
                calculated_shares = int(
                    (auth_amount_val / effective_face_value).quantize(Decimal("1"))
                )
                validated_data["authorized_capital_shares"] = calculated_shares
            elif auth_shares_provided and auth_shares_val and not auth_amount_provided:
                # Shares provided, calculate amount
                calculated_amount = Decimal(auth_shares_val) * effective_face_value
                validated_data["authorized_capital_amount"] = (
                    calculated_amount.quantize(Decimal("0.01"))
                )
            elif (
                not auth_amount_provided
                and not auth_shares_provided
                and auth_shares_val
            ):
                # Neither provided but instance has shares, calculate amount
                calculated_amount = Decimal(auth_shares_val) * effective_face_value
                validated_data["authorized_capital_amount"] = (
                    calculated_amount.quantize(Decimal("0.01"))
                )

            # ISSUED CAPITAL - Calculate missing field (amount or shares)
            issued_amount_provided = "issued_capital_amount" in validated_data
            issued_shares_provided = "issued_capital_shares" in validated_data
            issued_amount_val = validated_data.get(
                "issued_capital_amount", issued_amount
            )
            issued_shares_val = validated_data.get(
                "issued_capital_shares", issued_shares
            )

            if (
                issued_amount_provided
                and issued_amount_val
                and not issued_shares_provided
            ):
                # Amount provided, calculate shares
                calculated_shares = int(
                    (issued_amount_val / effective_face_value).quantize(Decimal("1"))
                )
                validated_data["issued_capital_shares"] = calculated_shares
            elif (
                issued_shares_provided
                and issued_shares_val
                and not issued_amount_provided
            ):
                # Shares provided, calculate amount
                calculated_amount = Decimal(issued_shares_val) * effective_face_value
                validated_data["issued_capital_amount"] = calculated_amount.quantize(
                    Decimal("0.01")
                )
            elif (
                not issued_amount_provided
                and not issued_shares_provided
                and issued_shares_val
            ):
                # Neither provided but instance has shares, calculate amount
                calculated_amount = Decimal(issued_shares_val) * effective_face_value
                validated_data["issued_capital_amount"] = calculated_amount.quantize(
                    Decimal("0.01")
                )

            # PAID-UP CAPITAL - Calculate missing field (amount or shares)
            paid_amount_provided = "paid_up_capital_amount" in validated_data
            paid_shares_provided = "paid_up_capital_shares" in validated_data
            paid_amount_val = validated_data.get(
                "paid_up_capital_amount", paid_up_amount
            )
            paid_shares_val = validated_data.get(
                "paid_up_capital_shares", paid_up_shares
            )

            if paid_amount_provided and paid_amount_val and not paid_shares_provided:
                # Amount provided, calculate shares
                calculated_shares = int(
                    (paid_amount_val / effective_face_value).quantize(Decimal("1"))
                )
                validated_data["paid_up_capital_shares"] = calculated_shares
            elif paid_shares_provided and paid_shares_val and not paid_amount_provided:
                # Shares provided, calculate amount
                calculated_amount = Decimal(paid_shares_val) * effective_face_value
                validated_data["paid_up_capital_amount"] = calculated_amount.quantize(
                    Decimal("0.01")
                )
            elif (
                not paid_amount_provided
                and not paid_shares_provided
                and paid_shares_val
            ):
                # Neither provided but instance has shares, calculate amount
                calculated_amount = Decimal(paid_shares_val) * effective_face_value
                validated_data["paid_up_capital_amount"] = calculated_amount.quantize(
                    Decimal("0.01")
                )

        # Update local variables after calculations
        authorized_amount = validated_data.get(
            "authorized_capital_amount", authorized_amount
        )
        issued_amount = validated_data.get("issued_capital_amount", issued_amount)
        paid_up_amount = validated_data.get("paid_up_capital_amount", paid_up_amount)
        authorized_shares = validated_data.get(
            "authorized_capital_shares", authorized_shares
        )
        issued_shares = validated_data.get("issued_capital_shares", issued_shares)
        paid_up_shares = validated_data.get("paid_up_capital_shares", paid_up_shares)
        face_value = validated_data.get(
            "face_value_per_share", face_value or effective_face_value
        )

        # Validate amounts
        if authorized_amount is not None and issued_amount is not None:
            if authorized_amount <= issued_amount:
                raise serializers.ValidationError(
                    {
                        "authorized_capital_amount": "Authorized Capital must be greater than Issued Capital."
                    }
                )

        if issued_amount is not None and paid_up_amount is not None:
            if issued_amount < paid_up_amount:
                raise serializers.ValidationError(
                    {
                        "paid_up_capital_amount": "Paid-up Capital cannot exceed Issued Capital."
                    }
                )

        # Validate shares
        if authorized_shares is not None and issued_shares is not None:
            if authorized_shares <= issued_shares:
                raise serializers.ValidationError(
                    {
                        "authorized_capital_shares": "Authorized shares must be greater than issued shares."
                    }
                )

        if issued_shares is not None and paid_up_shares is not None:
            if issued_shares < paid_up_shares:
                raise serializers.ValidationError(
                    {
                        "paid_up_capital_shares": "Paid-up shares cannot exceed issued shares."
                    }
                )

        # Validate ESOP pool
        esop_pool_size = validated_data.get("esop_pool_size")
        if esop_pool_size is None and instance:
            esop_pool_size = instance.esop_pool_size

        esop_pool_percentage = validated_data.get("esop_pool_percentage")
        if esop_pool_percentage is None and instance:
            esop_pool_percentage = instance.esop_pool_percentage

        if esop_pool_size is not None and authorized_shares is not None:
            if esop_pool_size > authorized_shares:
                raise serializers.ValidationError(
                    {
                        "esop_pool_size": "ESOP pool size cannot exceed authorized shares."
                    }
                )

        # Auto-sync ESOP pool percentage and size
        if authorized_shares and authorized_shares > 0:
            if (
                esop_pool_size is not None
                and "esop_pool_percentage" not in validated_data
            ):
                # Calculate percentage from size
                calculated_percentage = (
                    Decimal(esop_pool_size) / Decimal(authorized_shares)
                ) * Decimal("100")
                validated_data["esop_pool_percentage"] = calculated_percentage.quantize(
                    Decimal("0.01")
                )

            if (
                esop_pool_percentage is not None
                and "esop_pool_size" not in validated_data
            ):
                # Calculate size from percentage
                calculated_size = int(
                    (Decimal(esop_pool_percentage) / Decimal("100"))
                    * Decimal(authorized_shares)
                )
                validated_data["esop_pool_size"] = calculated_size

        return validated_data
