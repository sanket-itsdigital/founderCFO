from decimal import Decimal

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from accounts.models import Company, TeamMember
from accounts.serializers.company import CompanySerializer
from captable.models import (
    CapTableEventDocument,
    CapTableEvents,
    CapitalizationTable,
    Shareholder,
)
from captable.serializers import (
    CapTableEventDetailSerializer,
    CapTableEventDocumentSerializer,
    CapTableEventDocumentUploadSerializer,
    CapTableEventListSerializer,
    CapTableEventSerializer,
    CapTableEventTransactionCreateSerializer,
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


class ShareholderListCreateView(CompanyScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ShareholderSerializer

    def get_queryset(self):
        return Shareholder.objects.filter(**self._company_filter()).order_by("name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class ShareholderDetailView(CompanyScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ShareholderSerializer

    def get_queryset(self):
        return Shareholder.objects.filter(**self._company_filter()).order_by("name")

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CapTableEventListCreateView(CompanyScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            CapTableEvents.objects.filter(**self._company_filter())
            .select_related("company")
            .prefetch_related("documents", "transactions__shareholder")
        )

    def get_serializer_class(self):
        if self.request.method.lower() == "get":
            return CapTableEventListSerializer
        return CapTableEventSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class CapTableEventDetailView(
    CompanyScopedMixin, generics.RetrieveUpdateDestroyAPIView
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            CapTableEvents.objects.filter(**self._company_filter())
            .select_related("company")
            .prefetch_related("documents", "transactions__shareholder")
        )

    def get_serializer_class(self):
        if self.request.method.lower() == "get":
            return CapTableEventDetailSerializer
        return CapTableEventSerializer

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CapTableEventDocumentView(CompanyScopedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def _get_event(self, pk):
        filters = self._company_filter()
        event = get_object_or_404(CapTableEvents, pk=pk, **filters)
        return event

    def post(self, request, pk):
        event = self._get_event(pk)
        data = request.data.copy()
        files = request.FILES.getlist("files")
        if files:
            data.setlist("files", files)
        single_file = request.FILES.get("file")
        if single_file:
            data["file"] = single_file
        serializer = CapTableEventDocumentUploadSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        documents = serializer.save(event=event, user=request.user)
        response_serializer = CapTableEventDocumentSerializer(documents, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        event = self._get_event(pk)
        serializer = CapTableEventDocumentSerializer(event.documents.all(), many=True)
        return Response(serializer.data)


class CapitalizationTableListCreateView(CompanyScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CapitalizationTableSerializer

    def get_queryset(self):
        queryset = CapitalizationTable.objects.filter(
            **self._company_filter()
        ).select_related("event", "shareholder", "company")
        event_id = self.request.query_params.get("event_id")
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset.order_by("-event__date", "-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class CapitalizationTableDetailView(
    CompanyScopedMixin, generics.RetrieveUpdateDestroyAPIView
):
    permission_classes = [IsAuthenticated]
    serializer_class = CapitalizationTableSerializer

    def get_queryset(self):
        return (
            CapitalizationTable.objects.filter(**self._company_filter())
            .select_related("event", "shareholder", "company")
            .order_by("-event__date", "-created_at")
        )

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
                (shares / total_shares) * Decimal("100")
                if total_shares
                else Decimal("0")
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


class ShareHolderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)
        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        shareholders = Shareholder.objects.filter(company=company).order_by("name")
        serializer = ShareholderSerializer(shareholders, many=True)
        return Response(serializer.data)


class CompanyInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_qs = (
            Company.objects.filter(
                Q(owner=request.user)
                | Q(team_members__user=request.user, team_members__is_active=True)
            )
            .distinct()
            .order_by("name")
        )
        company_id = request.query_params.get("company_id")
        if company_id:
            company = get_object_or_404(company_qs, id=company_id)
            serializer = CompanySerializer(company)
            return Response(serializer.data)
        serializer = CompanySerializer(company_qs, many=True)
        return Response(serializer.data)


class CapTableEventTransactionCreateView(CompanyScopedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def _get_queryset(self):
        return (
            CapTableEvents.objects.filter(**self._company_filter())
            .select_related("company")
            .prefetch_related("documents", "transactions__shareholder")
            .order_by("-date")
        )

    def get(self, request):
        queryset = self._get_queryset()
        serializer = CapTableEventDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CapTableEventTransactionCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        event, transactions = serializer.save()
        event_data = CapTableEventDetailSerializer(event).data
        tx_data = CapitalizationTableSerializer(transactions, many=True).data
        return Response(
            {
                "event": event_data,
                "transactions": tx_data,
            },
            status=status.HTTP_201_CREATED,
        )


class CapTableEventTransactionDetailView(CompanyScopedMixin, generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CapTableEventDetailSerializer

    def get_queryset(self):
        return (
            CapTableEvents.objects.filter(**self._company_filter())
            .select_related("company")
            .prefetch_related("documents", "transactions__shareholder")
        )
