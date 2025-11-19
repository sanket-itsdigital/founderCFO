from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from captable.models import (
    CapTableEventDocument,
    CapTableEvents,
    CapitalizationTable,
    Shareholder,
)
from captable.serializers import (
    CapTableEventDetailSerializer,
    CapTableEventDocumentSerializer,
    CapTableEventListSerializer,
    CapTableEventSerializer,
    CapitalizationTableSerializer,
    ShareholderSerializer,
)


class CompanyScopedMixin:
    def _company_filter(self):
        if getattr(self, "swagger_fake_view", False):
            return {}
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return {}
        company_id = self.request.query_params.get("company_id")
        filters = {"company__owner": user}
        if company_id:
            filters["company_id"] = company_id
        return filters


class ShareholderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ShareholderSerializer

    def get_queryset(self):
        return Shareholder.objects.filter(
            **self._company_filter()
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CapTableEventViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CapTableEventSerializer

    def get_queryset(self):
        return (
            CapTableEvents.objects.filter(**self._company_filter())
            .select_related("company")
            .prefetch_related("documents", "transactions__shareholder")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CapTableEventListSerializer
        if self.action == "retrieve":
            return CapTableEventDetailSerializer
        if self.action == "upload_document":
            return CapTableEventDocumentSerializer
        return CapTableEventSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="documents",
        permission_classes=[IsAuthenticated],
    )
    def upload_document(self, request, pk=None):
        event = self.get_object()
        serializer = CapTableEventDocumentSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(event=event, created_by=request.user, updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @upload_document.mapping.get
    def list_documents(self, request, pk=None):
        event = self.get_object()
        serializer = CapTableEventDocumentSerializer(event.documents.all(), many=True)
        return Response(serializer.data)


class CapitalizationTableViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CapitalizationTableSerializer

    def get_queryset(self):
        return (
            CapitalizationTable.objects.filter(**self._company_filter())
            .select_related("event", "shareholder", "company")
            .order_by("-event__date", "-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CapTableSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)
        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        rows = (
            CapitalizationTable.objects.filter(company=company)
            .select_related("shareholder")
            .order_by("shareholder__name")
        )
        total_shares = Decimal("0")
        summary = {}
        for row in rows:
            total_shares += row.shares_issued or Decimal("0")
            shareholder = row.shareholder
            if not shareholder:
                continue
            info = summary.setdefault(
                shareholder.id,
                {
                    "shareholder_id": shareholder.id,
                    "name": shareholder.name,
                    "investor_type": shareholder.investor_type,
                    "email": shareholder.email,
                    "kyc_verified": shareholder.kyc_verified,
                    "total_shares": Decimal("0"),
                    "total_invested": Decimal("0"),
                },
            )
            info["total_shares"] += row.shares_issued or Decimal("0")
            info["total_invested"] += row.amount or Decimal("0")

        shareholder_rows = []
        for data in summary.values():
            shares = data["total_shares"]
            ownership = (
                (shares / total_shares) * Decimal("100") if total_shares else Decimal("0")
            )
            shareholder_rows.append(
                {
                    **data,
                    "ownership_percent": round(ownership, 2),
                }
            )

        return Response(
            {
                "company_id": company_id,
                "total_shares_outstanding": total_shares,
                "shareholders": shareholder_rows,
            }
        )

