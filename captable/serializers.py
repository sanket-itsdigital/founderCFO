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
        company = getattr(self, "_company", None)
        if company_id and not company:
            company = self._get_company(company_id)
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
    shareholder = ShareholderSerializer(read_only=True)
    total_invested = serializers.SerializerMethodField()

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
            "created_at",
        )
        read_only_fields = ("id", "amount", "total_invested", "created_at")
        extra_kwargs = {
            "event_id": {"write_only": True},
            "shareholder_id": {"write_only": True},
        }

    def get_total_invested(self, obj):
        return obj.amount

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
    shareholder_summary = serializers.SerializerMethodField()

    class Meta(CapTableEventListSerializer.Meta):
        fields = CapTableEventListSerializer.Meta.fields + (
            "notes",
            "documents",
            "transactions",
            "shareholder_summary",
        )

    def get_shareholder_summary(self, obj):
        summary = {}
        for tx in obj.transactions.all():
            shareholder = tx.shareholder
            if not shareholder:
                continue
            info = summary.setdefault(
                shareholder.id,
                {
                    "shareholder_id": shareholder.id,
                    "name": shareholder.name,
                    "investor_type": shareholder.investor_type,
                    "email": shareholder.email,
                    "total_shares": Decimal("0"),
                    "total_invested": Decimal("0"),
                },
            )
            info["total_shares"] += tx.shares_issued or Decimal("0")
            info["total_invested"] += tx.amount or Decimal("0")
        return list(summary.values())


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
            instance.company = self._get_company(company_id)
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

        company_id = attrs.get("company_id") or getattr(self, "_company", None)
        if company_id:
            if isinstance(company_id, str):
                company = self._get_company(company_id)
            else:
                company = company_id
        else:
            company = getattr(self, "_company", None)

        if not company:
            # Will be validated in create method
            return validated_data

        # Check if this is an update
        instance = getattr(self, "instance", None)
        total_options = attrs.get("total_options")
        if total_options is None and instance:
            total_options = instance.total_options

        if total_options and company.esop_pool_size:
            # Calculate total granted options (excluding current grant if updating)
            existing_grants = ESOPGrant.objects.filter(company=company, status="Active")
            if instance:
                existing_grants = existing_grants.exclude(id=instance.id)

            total_granted = sum(grant.total_options for grant in existing_grants)
            new_total = total_granted + total_options

            if new_total > company.esop_pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({new_total}) would exceed ESOP pool size "
                            f"({company.esop_pool_size}). Available: {company.esop_pool_size - total_granted}"
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
        total_options = validated_data.get("total_options", 0)
        if total_options and company.esop_pool_size:
            existing_grants = ESOPGrant.objects.filter(company=company, status="Active")
            total_granted = sum(grant.total_options for grant in existing_grants)
            if total_granted + total_options > company.esop_pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({total_granted + total_options}) would exceed "
                            f"ESOP pool size ({company.esop_pool_size}). Available: "
                            f"{company.esop_pool_size - total_granted}"
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
        if total_options and company.esop_pool_size:
            existing_grants = ESOPGrant.objects.filter(
                company=company, status="Active"
            ).exclude(id=instance.id)
            total_granted = sum(grant.total_options for grant in existing_grants)
            if total_granted + total_options > company.esop_pool_size:
                raise serializers.ValidationError(
                    {
                        "total_options": (
                            f"Total granted options ({total_granted + total_options}) would exceed "
                            f"ESOP pool size ({company.esop_pool_size}). Available: "
                            f"{company.esop_pool_size - total_granted}"
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
