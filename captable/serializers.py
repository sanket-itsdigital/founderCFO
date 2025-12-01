from decimal import Decimal
import uuid

from django.db import transaction
from rest_framework import serializers

from accounts.models import Company
from captable.enums import InvestorType, ShareClassType
from captable.models import (
    CapTableEventDocument,
    CapTableEvents,
    CapitalizationTable,
    ESOPGrant,
    VestingSchedule,
    Shareholder,
)


class CompanyScopedSerializerMixin:
    def _get_company(self, value):
        request = self.context.get("request")
        if not request:
            return None
        try:
            return Company.objects.get(id=value, owner=request.user)
        except Company.DoesNotExist as exc:  # pragma: no cover - defensive
            raise serializers.ValidationError("Invalid company.") from exc


class ShareholderSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    company_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Shareholder
        fields = (
            "id",
            "company_id",
            "name",
            "investor_type",
            "email",
            "kyc_verified",
            "created_at",
        )
        read_only_fields = ("id", "created_at")



    def validate_company_id(self, value):
        self._company = self._get_company(value)
        return value

    def create(self, validated_data, **kwargs):
        company_id = validated_data.pop("company_id", None)
        company = self._resolve_company_instance(company_id)
        if not company:
            raise serializers.ValidationError({"company_id": "Company is required."})
        return Shareholder.objects.create(company=company, **validated_data, **kwargs)


class CapTableEventDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapTableEventDocument
        fields = ("id", "name", "file", "created_at")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        if not validated_data.get("name") and validated_data.get("file"):
            validated_data["name"] = validated_data["file"].name
        return super().create(validated_data)


class CapTableEventDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=False,
    )
    names = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        required=False,
    )

    def validate(self, attrs):
        file = attrs.get("file")
        files = attrs.get("files")
        if not file and not files:
            raise serializers.ValidationError("Provide at least one file.")
        if file and files:
            raise serializers.ValidationError("Use either 'file' or 'files', not both.")

        names = attrs.get("names") or []
        expected_length = 1 if file else len(files or [])
        if names and len(names) not in (0, expected_length):
            raise serializers.ValidationError(
                {"names": "Provide one name per uploaded file."}
            )
        return attrs

    def save(self, *, event, user):
        files = list(self.validated_data.get("files") or [])
        file = self.validated_data.get("file")
        if file:
            files = [file]
        names = self.validated_data.get("names") or []

        documents = []
        for index, uploaded_file in enumerate(files):
            name = names[index] if index < len(names) else uploaded_file.name
            document = CapTableEventDocument.objects.create(
                event=event,
                name=name,
                file=uploaded_file,
                created_by=user,
                updated_by=user,
            )
            documents.append(document)
        return documents


class CapitalizationTableSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField(write_only=True)
    shareholder_id = serializers.UUIDField(write_only=True)
    shareholder = serializers.SerializerMethodField()
    total_invested = serializers.SerializerMethodField()
    cumulative_shares = serializers.SerializerMethodField()
    ownership_percentage = serializers.SerializerMethodField()
    
    def get_shareholder(self, obj):
        """Return shareholder with ownership percentage."""
        shareholder_data = ShareholderSerializer(obj.shareholder, context=self.context).data
        
        # Calculate ownership percentage for this shareholder
        company = obj.company
        shareholder = obj.shareholder
        event_date = obj.event.date
        
        # Get cumulative shares for this shareholder
        shareholder_shares = Decimal("0")
        shareholder_transactions = CapitalizationTable.objects.filter(
            company=company,
            shareholder=shareholder,
            event__date__lte=event_date
        )
        for tx in shareholder_transactions:
            shareholder_shares += tx.shares_issued or Decimal("0")
        
        # Get total issued shares up to this event
        total_issued = Decimal("0")
        all_transactions = CapitalizationTable.objects.filter(
            company=company,
            event__date__lte=event_date
        )
        for tx in all_transactions:
            total_issued += tx.shares_issued or Decimal("0")
        
        # Calculate ownership percentage
        ownership_pct = 0.0
        if total_issued > 0:
            ownership_pct = float((shareholder_shares / total_issued) * Decimal("100"))
        
        # Add ownership percentage to shareholder data
        shareholder_data["ownership_percentage"] = round(ownership_pct, 2)
        
        return shareholder_data

    class Meta:
        model = CapitalizationTable
        fields = (
            "id",
            "event_id",
            "shareholder_id",
            "shareholder",
            "event",
            "share_class_type",
            "share_class_name",
            "shares_issued",
            "price_per_share",
            "lock_in_ends",
            "amount",
            "total_invested",
            "cumulative_shares",
            "ownership_percentage",
            "created_at",
        )
        read_only_fields = ("id", "amount", "total_invested", "cumulative_shares", "ownership_percentage", "created_at")
        extra_kwargs = {
            "event_id": {"write_only": True},
            "shareholder_id": {"write_only": True},
        }

    def get_total_invested(self, obj):
        return obj.amount

    def get_cumulative_shares(self, obj):
        """Calculate cumulative shares for this shareholder up to this event."""
        company = obj.company
        shareholder = obj.shareholder
        event_date = obj.event.date
        
        # Sum all shares for this shareholder from events up to and including this event
        total = Decimal("0")
        transactions = CapitalizationTable.objects.filter(
            company=company,
            shareholder=shareholder,
            event__date__lte=event_date
        )
        for tx in transactions:
            total += tx.shares_issued or Decimal("0")
        return float(total)

    def get_ownership_percentage(self, obj):
        """Calculate ownership percentage for this shareholder up to this event."""
        company = obj.company
        shareholder = obj.shareholder
        event_date = obj.event.date
        
        # Get cumulative shares for this shareholder
        shareholder_shares = Decimal("0")
        shareholder_transactions = CapitalizationTable.objects.filter(
            company=company,
            shareholder=shareholder,
            event__date__lte=event_date
        )
        for tx in shareholder_transactions:
            shareholder_shares += tx.shares_issued or Decimal("0")
        
        # Get total issued shares up to this event
        total_issued = Decimal("0")
        all_transactions = CapitalizationTable.objects.filter(
            company=company,
            event__date__lte=event_date
        )
        for tx in all_transactions:
            total_issued += tx.shares_issued or Decimal("0")
        
        if total_issued == 0:
            return 0.0
        
        percentage = (shareholder_shares / total_issued) * Decimal("100")
        return round(float(percentage), 2)

    def _get_event(self, event_id):
        request = self.context.get("request")
        qs = CapTableEvents.objects.filter(company__owner=request.user)
        try:
            return qs.get(id=event_id)
        except CapTableEvents.DoesNotExist as exc:
            raise serializers.ValidationError({"event_id": "Event not found."}) from exc

    def _get_shareholder(self, shareholder_id, company):
        request = self.context.get("request")
        qs = Shareholder.objects.filter(company=company, company__owner=request.user)
        try:
            return qs.get(id=shareholder_id)
        except Shareholder.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"shareholder_id": "Shareholder not found for this company."}
            ) from exc

    def create(self, validated_data, **kwargs):
        event = self._get_event(validated_data.pop("event_id"))
        shareholder = self._get_shareholder(
            validated_data.pop("shareholder_id"), event.company
        )
        return CapitalizationTable.objects.create(
            company=event.company,
            event=event,
            shareholder=shareholder,
            **validated_data,
            **kwargs,
        )

    def update(self, instance, validated_data, **kwargs):
        event_id = validated_data.pop("event_id", None)
        shareholder_id = validated_data.pop("shareholder_id", None)
        if event_id:
            instance.event = self._get_event(event_id)
            instance.company = instance.event.company
        if shareholder_id:
            instance.shareholder = self._get_shareholder(
                shareholder_id, instance.company
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        for attr, value in kwargs.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CapTableEventListSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source="company.id", read_only=True)
    documents_count = serializers.SerializerMethodField()
    total_shares = serializers.SerializerMethodField()
    total_invested = serializers.SerializerMethodField()

    class Meta:
        model = CapTableEvents
        fields = (
            "id",
            "company_id",
            "event_name",
            "event_type",
            "date",
            "description",
            "valuation",
            "amount_raised",
            "share_price",
            "documents_count",
            "total_shares",
            "total_invested",
        )

    def get_documents_count(self, obj):
        return getattr(obj, "_documents_count", None) or obj.documents.count()

    def _aggregate_transactions(self, obj):
        total_shares = Decimal("0")
        total_invested = Decimal("0")
        transactions = obj.transactions.all()
        for tx in transactions:
            total_shares += tx.shares_issued or Decimal("0")
            total_invested += tx.amount or Decimal("0")
        return total_shares, total_invested

    def get_total_shares(self, obj):
        return self._aggregate_transactions(obj)[0]

    def get_total_invested(self, obj):
        return self._aggregate_transactions(obj)[1]


class CapTableEventDetailSerializer(CapTableEventListSerializer):
    documents = CapTableEventDocumentSerializer(many=True, read_only=True)
    transactions = CapitalizationTableSerializer(many=True, read_only=True)

    class Meta(CapTableEventListSerializer.Meta):
        fields = CapTableEventListSerializer.Meta.fields + (
            "notes",
            "documents",
            "transactions",
        )


class CapTableEventSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    company_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = CapTableEvents
        fields = (
            "id",
            "company_id",
            "event_name",
            "event_type",
            "date",
            "description",
            "valuation",
            "amount_raised",
            "share_price",
            "notes",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_company_id(self, value):
        self._company = self._get_company(value)
        return value

    def create(self, validated_data, **kwargs):
        company_id = validated_data.pop("company_id", None)
        company = getattr(self, "_company", None)
        if company_id and not company:
            company = self._get_company(company_id)
        if not company:
            raise serializers.ValidationError({"company_id": "Company is required."})
        return CapTableEvents.objects.create(
            company=company, **validated_data, **kwargs
        )


class CapTableEventTransactionLineSerializer(serializers.Serializer):
    shareholder_id = serializers.UUIDField()
    share_class_type = serializers.ChoiceField(choices=ShareClassType.choices)
    share_class_name = serializers.CharField(max_length=255)
    shares_issued = serializers.DecimalField(max_digits=20, decimal_places=2)
    price_per_share = serializers.DecimalField(max_digits=20, decimal_places=4)
    lock_in_ends = serializers.DateField(required=False, allow_null=True)

    def validate_shares_issued(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Shares issued must be greater than zero."
            )
        return value

    def validate_price_per_share(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price per share must be greater than zero."
            )
        return value


class CapTableEventTransactionCreateSerializer(serializers.Serializer):
    event = CapTableEventSerializer()
    transactions = CapTableEventTransactionLineSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")

        event_data = attrs.get("event") or {}
        event_serializer = CapTableEventSerializer(
            data=event_data, context=self.context
        )
        event_serializer.is_valid(raise_exception=True)
        self._event_serializer = event_serializer

        share_price = event_serializer.validated_data.get("share_price")
        if share_price is None:
            raise serializers.ValidationError(
                {"event": {"share_price": "Share price is required."}}
            )

        company = getattr(event_serializer, "_company", None)
        if not company:
            company_id = event_serializer.validated_data.get("company_id")
            if company_id:
                company = event_serializer._get_company(company_id)
        if not company:
            raise serializers.ValidationError(
                {"event": {"company_id": "Company is required."}}
            )

        shareholder_cache = {}
        enriched_transactions = []
        for index, tx in enumerate(attrs["transactions"]):
            shareholder_id = tx["shareholder_id"]
            shareholder = shareholder_cache.get(shareholder_id)
            if not shareholder:
                try:
                    shareholder = Shareholder.objects.get(
                        id=shareholder_id, company=company, company__owner=request.user
                    )
                except Shareholder.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {
                            "transactions": [
                                f"Shareholder {shareholder_id} not found for this company."
                            ]
                        }
                    ) from exc
                shareholder_cache[shareholder_id] = shareholder

            if tx["price_per_share"] != share_price:
                raise serializers.ValidationError(
                    {
                        "transactions": [
                            f"Line {index + 1}: price_per_share must equal the event share_price ({share_price})."
                        ]
                    }
                )

            enriched_transactions.append({**tx, "shareholder": shareholder})

        attrs["transactions"] = enriched_transactions
        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        event_serializer = getattr(self, "_event_serializer")
        transaction_payloads = self.validated_data["transactions"]

        with transaction.atomic():
            event = event_serializer.save(created_by=user, updated_by=user)
            created_transactions = []
            for tx in transaction_payloads:
                shareholder = tx.pop("shareholder")
                row = CapitalizationTable.objects.create(
                    company=event.company,
                    event=event,
                    shareholder=shareholder,
                    created_by=user,
                    updated_by=user,
                    **tx,
                )
                created_transactions.append(row)
        return event, created_transactions


class VestingScheduleSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    company_id = serializers.UUIDField(write_only=True, required=False)
    employees_count = serializers.SerializerMethodField()
    linked_employees = serializers.SerializerMethodField()

    class Meta:
        model = VestingSchedule
        fields = (
            "id",
            "company_id",
            "name",
            "total_shares",
            "start_date",
            "vesting_frequency",
            "cliff_period_months",
            "total_vesting_period_months",
            "single_trigger",
            "double_trigger",
            "notes",
            "employees_count",
            "linked_employees",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "employees_count",
            "linked_employees",
        )

    def validate_company_id(self, value):
        self._company = self._get_company(value)
        return value

    def validate(self, attrs):
        cliff = attrs.get("cliff_period_months")
        total = attrs.get("total_vesting_period_months")
        if self.instance:
            if cliff is None:
                cliff = self.instance.cliff_period_months
            if total is None:
                total = self.instance.total_vesting_period_months
        if cliff and total and total < cliff:
            raise serializers.ValidationError(
                {"total_vesting_period_months": "Total period must be >= cliff period."}
            )
        return attrs

    def create(self, validated_data, **kwargs):
        company_id = validated_data.pop("company_id", None)
        company = getattr(self, "_company", None)
        if company_id and not company:
            company = self._get_company(company_id)
        if not company:
            raise serializers.ValidationError({"company_id": "Company is required."})
        return VestingSchedule.objects.create(
            company=company,
            **validated_data,
            **kwargs,
        )

    def update(self, instance, validated_data, **kwargs):
        company_id = validated_data.pop("company_id", None)
        if company_id:
            instance.company = self._resolve_company_instance(company_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        for attr, value in kwargs.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance

    def get_employees_count(self, obj):
        """Count unique employees using this vesting schedule."""
        if not obj.pk:
            return 0
        return (
            obj.esop_grants.filter(status="Active")
            .values("employee_email")
            .distinct()
            .count()
        )

    def get_linked_employees(self, obj):
        """Get list of employees linked to this vesting schedule with their grant details."""
        if not obj.pk:
            return []

        grants = obj.esop_grants.filter(status="Active").select_related()
        employee_data = {}

        for grant in grants:
            email = grant.employee_email
            if email not in employee_data:
                progress, vested, unvested = grant.calculate_vesting_metrics()
                employee_data[email] = {
                    "employee_name": grant.employee_name,
                    "employee_email": email,
                    "total_options": 0,
                    "vested_options": 0,
                    "unvested_options": 0,
                    "vested_percentage": float(progress),
                }

            # Aggregate options across all grants for this employee
            employee_data[email]["total_options"] += grant.total_options
            _, vested, unvested = grant.calculate_vesting_metrics()
            employee_data[email]["vested_options"] += int(vested)
            employee_data[email]["unvested_options"] += int(unvested)

        # Recalculate vested percentage after aggregation
        for email, data in employee_data.items():
            if data["total_options"] > 0:
                percentage = (
                    (Decimal(data["vested_options"]) / Decimal(data["total_options"]))
                    * Decimal("100")
                ).quantize(Decimal("0.1"))
                data["vested_percentage"] = float(percentage)
            else:
                data["vested_percentage"] = 0.0

        return list(employee_data.values())


class ESOPGrantSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    company_id = serializers.UUIDField(write_only=True, required=False)
    vesting_schedule_plan = VestingScheduleSerializer(read_only=True)
    vesting_progress_percent = serializers.SerializerMethodField()
    vested_options = serializers.SerializerMethodField()
    unvested_options = serializers.SerializerMethodField()

    class Meta:
        model = ESOPGrant
        fields = (
            "id",
            "company_id",
            "employee_name",
            "employee_email",
            "grant_date",
            "cliff_date",
            "total_options",
            "strike_price",
            "fair_market_value",
            "exercise_window_days",
            "vesting_schedule",
            "vesting_schedule_plan",
            "vesting_progress_percent",
            "vested_options",
            "unvested_options",
            "grant_type",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_company_id(self, value):
        self._company = self._get_company(value)
        return value

    def _resolve_company_instance(self, company_id=None):
        """
        Ensure we always work with a Company instance.
        Accepts UUID/str/Company or falls back to self._company.
        """
        company = None
        candidate = company_id or getattr(self, "_company", None)

        if isinstance(candidate, Company):
            company = candidate
        elif candidate:
            # Accept UUID objects or strings
            company = self._get_company(str(candidate))

        return company

    def _get_vesting_schedule(self, schedule_id, company):
        request = self.context.get("request")
        qs = VestingSchedule.objects.filter(company=company)
        if request and getattr(request, "user", None):
            qs = qs.filter(company__owner=request.user)
        try:
            return qs.get(id=schedule_id)
        except VestingSchedule.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"vesting_schedule": "Vesting schedule not found for this company."}
            ) from exc

    def _resolve_vesting_schedule(self, schedule_value, company):
        if schedule_value in (None, ""):
            return schedule_value, None
        try:
            schedule_uuid = uuid.UUID(str(schedule_value))
        except (ValueError, TypeError):
            return schedule_value, None
        schedule = self._get_vesting_schedule(schedule_uuid, company)
        return schedule.name, schedule

    def validate(self, attrs):
        """Validate that total grants don't exceed ESOP pool size."""
        validated_data = (
            super().validate(attrs) if hasattr(super(), "validate") else attrs
        )

        company = self._resolve_company_instance(attrs.get("company_id"))

        if not company:
            # Will be validated in create method
            return validated_data

        # Check if this is an update
        instance = getattr(self, "instance", None)
        total_options = attrs.get("total_options")
        if total_options is None and instance:
            total_options = instance.total_options

        # Validation 1: If pool size is 0 or None, cannot assign grants
        pool_size = company.esop_pool_size or 0
        if pool_size == 0:
            raise serializers.ValidationError(
                {
                    "total_options": (
                        "Cannot assign grants when ESOP pool size is 0. "
                        "Please configure the ESOP pool size first."
                    )
                }
            )

        # Validation 2: Pool size must be >= total grants (wasted + unwasted)
        if total_options:
            # Calculate total granted options from ALL grants (all statuses: Active, Cancelled, Exercised)
            existing_grants = ESOPGrant.objects.filter(company=company)
            if instance:
                existing_grants = existing_grants.exclude(id=instance.id)

            total_granted = sum(grant.total_options for grant in existing_grants)
            new_total = total_granted + total_options

            if new_total > pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({new_total}) would exceed ESOP pool size "
                            f"({pool_size}). Available: {pool_size - total_granted}"
                        )
                    }
                )

        # Validation 3: Unique grant per employee per grant date
        employee_email = attrs.get("employee_email") or getattr(instance, "employee_email", None)
        grant_date = attrs.get("grant_date") or getattr(instance, "grant_date", None)
        if company and employee_email and grant_date:
            duplicate_qs = ESOPGrant.objects.filter(
                company=company,
                employee_email=employee_email,
                grant_date=grant_date,
            )
            if instance:
                duplicate_qs = duplicate_qs.exclude(id=instance.id)
            if duplicate_qs.exists():
                raise serializers.ValidationError(
                    {
                        "grant_date": (
                            "An ESOP grant for this employee and grant date already exists. "
                            "Please pick a different date or update the existing grant."
                        )
                    }
                )

        return validated_data

    def create(self, validated_data, **kwargs):
        company_id = validated_data.pop("company_id", None)
        company = getattr(self, "_company", None)
        if company_id and not company:
            company = self._get_company(company_id)
        if not company:
            raise serializers.ValidationError({"company_id": "Company is required."})

        # Validate against pool size
        pool_size = company.esop_pool_size or 0
        total_options = validated_data.get("total_options", 0)

        # Validation 1: If pool size is 0, cannot assign grants
        if pool_size == 0:
            raise serializers.ValidationError(
                {
                    "total_options": (
                        "Cannot assign grants when ESOP pool size is 0. "
                        "Please configure the ESOP pool size first."
                    )
                }
            )

        # Validation 2: Pool size must be >= total grants (wasted + unwasted)
        if total_options:
            # Calculate total from ALL grants (all statuses: Active, Cancelled, Exercised)
            existing_grants = ESOPGrant.objects.filter(company=company)
            total_granted = sum(grant.total_options for grant in existing_grants)
            if total_granted + total_options > pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({total_granted + total_options}) would exceed "
                            f"ESOP pool size ({pool_size}). Available: "
                            f"{pool_size - total_granted}"
                        )
                    }
                )

        schedule_value = validated_data.get("vesting_schedule")
        schedule_text, schedule = self._resolve_vesting_schedule(
            schedule_value, company
        )
        if schedule_text is not None and schedule_value is not None:
            validated_data["vesting_schedule"] = schedule_text
        return ESOPGrant.objects.create(
            company=company,
            vesting_schedule_plan=schedule,
            **validated_data,
            **kwargs,
        )

    def update(self, instance, validated_data):
        company_id = validated_data.pop("company_id", None)
        if company_id:
            instance.company = self._get_company(company_id)

        # Validate against pool size
        total_options = validated_data.get("total_options")
        if total_options is None:
            total_options = instance.total_options

        company = instance.company
        pool_size = company.esop_pool_size or 0

        # Validation 1: If pool size is 0, cannot assign grants
        if pool_size == 0:
            raise serializers.ValidationError(
                {
                    "total_options": (
                        "Cannot assign grants when ESOP pool size is 0. "
                        "Please configure the ESOP pool size first."
                    )
                }
            )

        # Validation 2: Pool size must be >= total grants (wasted + unwasted)
        if total_options:
            # Calculate total from ALL grants (all statuses: Active, Cancelled, Exercised)
            existing_grants = ESOPGrant.objects.filter(company=company).exclude(
                id=instance.id
            )
            total_granted = sum(grant.total_options for grant in existing_grants)
            if total_granted + total_options > pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({total_granted + total_options}) would exceed "
                            f"ESOP pool size ({pool_size}). Available: "
                            f"{pool_size - total_granted}"
                        )
                    }
                )

        if "vesting_schedule" in validated_data:
            schedule_value = validated_data["vesting_schedule"]
            schedule_text, schedule = self._resolve_vesting_schedule(
                schedule_value, instance.company
            )
            instance.vesting_schedule_plan = schedule
            validated_data["vesting_schedule"] = schedule_text
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance

    def _get_vesting_metrics(self, obj):
        progress, vested, unvested = obj.calculate_vesting_metrics()
        return progress, vested, unvested

    def get_vesting_progress_percent(self, obj):
        return self._get_vesting_metrics(obj)[0]

    def get_vested_options(self, obj):
        return self._get_vesting_metrics(obj)[1]

    def get_unvested_options(self, obj):
        return self._get_vesting_metrics(obj)[2]


class VestingScheduleDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = VestingSchedule
        fields = ("id", "name")


class EmployeeESOPDirectorySerializer(serializers.Serializer):
    """Serializer for Employee ESOP Directory listing."""

    employee_name = serializers.CharField()
    employee_email = serializers.EmailField()
    grants_count = serializers.IntegerField()
    total_options = serializers.IntegerField()
    vested_options = serializers.IntegerField()
    unvested_options = serializers.IntegerField()
    vesting_progress_percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class EmployeeGrantDetailSerializer(serializers.ModelSerializer):
    """Serializer for individual grant details in employee view."""

    vesting_progress_percent = serializers.SerializerMethodField()
    vested_options = serializers.SerializerMethodField()
    unvested_options = serializers.SerializerMethodField()

    class Meta:
        model = ESOPGrant
        fields = (
            "id",
            "grant_date",
            "total_options",
            "vested_options",
            "unvested_options",
            "strike_price",
            "status",
            "vesting_progress_percent",
        )

    def get_vesting_progress_percent(self, obj):
        progress, _, _ = obj.calculate_vesting_metrics()
        return float(progress)

    def get_vested_options(self, obj):
        _, vested, _ = obj.calculate_vesting_metrics()
        return int(vested)

    def get_unvested_options(self, obj):
        _, _, unvested = obj.calculate_vesting_metrics()
        return int(unvested)


class EmployeeESOPDetailSerializer(serializers.Serializer):
    """Serializer for Employee ESOP Details (Summary, Grants, Exercise History)."""

    employee_name = serializers.CharField()
    employee_email = serializers.EmailField()

    # Summary fields
    total_options = serializers.IntegerField()
    grants_count = serializers.IntegerField()
    total_vested_options = serializers.IntegerField()
    total_unvested_options = serializers.IntegerField()
    vested_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    exercisable_options = serializers.IntegerField()
    total_exercised = serializers.IntegerField()
    exercised_transactions_count = serializers.IntegerField()

    # Grants list
    grants = EmployeeGrantDetailSerializer(many=True)

    # Exercise history (for future implementation)
    exercise_history = serializers.ListField(
        child=serializers.DictField(), default=list
    )
