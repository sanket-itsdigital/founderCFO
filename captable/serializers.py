from decimal import Decimal

from rest_framework import serializers

from accounts.models import Company
from captable.enums import InvestorType
from captable.models import (
    CapTableEventDocument,
    CapTableEvents,
    CapitalizationTable,
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
            raise serializers.ValidationError(
                {"event_id": "Event not found."}
            ) from exc

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
        shareholder = self._get_shareholder(validated_data.pop("shareholder_id"), event.company)
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
            instance.shareholder = self._get_shareholder(shareholder_id, instance.company)
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


class CapTableEventSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
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
        return CapTableEvents.objects.create(company=company, **validated_data, **kwargs)

