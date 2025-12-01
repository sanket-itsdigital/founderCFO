from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
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
    ESOPGrant,
    Shareholder,
    VestingSchedule,
)
from captable.serializers import (
    CapTableEventDetailSerializer,
    CapTableEventDocumentSerializer,
    CapTableEventDocumentUploadSerializer,
    CapTableEventListSerializer,
    CapTableEventSerializer,
    CapTableEventTransactionCreateSerializer,
    CapitalizationTableSerializer,
    EmployeeESOPDetailSerializer,
    EmployeeESOPDirectorySerializer,
    EmployeeGrantDetailSerializer,
    ESOPGrantSerializer,
    ShareholderSerializer,
    VestingScheduleDropdownSerializer,
    VestingScheduleSerializer,
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


class ESOPGrantListCreateView(CompanyScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ESOPGrantSerializer

    def get_queryset(self):
        queryset = ESOPGrant.objects.filter(**self._company_filter())
        return queryset.select_related("company", "vesting_schedule_plan").order_by(
            "-grant_date", "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class ESOPGrantDetailView(CompanyScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ESOPGrantSerializer

    def get_queryset(self):
        return ESOPGrant.objects.filter(**self._company_filter()).select_related(
            "company",
            "vesting_schedule_plan",
        )

    def perform_update(self, serializer):
        """Updates an existing ESOP grant."""
        serializer.save(updated_by=self.request.user)


class VestingScheduleListCreateView(CompanyScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VestingScheduleSerializer

    def get_queryset(self):
        return (
            VestingSchedule.objects.filter(**self._company_filter())
            .prefetch_related("esop_grants")
            .order_by("name")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class VestingScheduleDetailView(
    CompanyScopedMixin, generics.RetrieveUpdateDestroyAPIView
):
    permission_classes = [IsAuthenticated]
    serializer_class = VestingScheduleSerializer

    def get_queryset(self):
        return (
            VestingSchedule.objects.filter(**self._company_filter())
            .prefetch_related("esop_grants")
            .order_by("name")
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class VestingScheduleDropdownListView(CompanyScopedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VestingScheduleDropdownSerializer

    def get_queryset(self):
        return VestingSchedule.objects.filter(**self._company_filter()).order_by("name")


class EmployeeESOPDirectoryView(APIView):
    """API endpoint for Employee ESOP Directory - list all employees with ESOP grants."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        search_query = request.query_params.get("search", "").strip()

        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        # Get all active grants for the company
        grants = ESOPGrant.objects.filter(
            company=company, status="Active"
        ).select_related("vesting_schedule_plan")

        # Filter by search query if provided
        if search_query:
            grants = grants.filter(
                Q(employee_name__icontains=search_query)
                | Q(employee_email__icontains=search_query)
            )

        # Aggregate by employee email
        employee_data = {}
        for grant in grants:
            email = grant.employee_email
            if email not in employee_data:
                employee_data[email] = {
                    "employee_name": grant.employee_name,
                    "employee_email": email,
                    "grants_count": 0,
                    "total_options": 0,
                    "vested_options": Decimal("0"),
                    "unvested_options": Decimal("0"),
                }

            employee_data[email]["grants_count"] += 1
            employee_data[email]["total_options"] += grant.total_options
            _, vested, unvested = grant.calculate_vesting_metrics()
            employee_data[email]["vested_options"] += vested
            employee_data[email]["unvested_options"] += unvested

        # Format response
        employees = []
        for email, data in employee_data.items():
            total = data["total_options"]
            vested = int(data["vested_options"])
            unvested = int(data["unvested_options"])
            progress = (
                (vested / Decimal(total) * Decimal("100")).quantize(Decimal("0.1"))
                if total > 0
                else Decimal("0")
            )

            employees.append(
                {
                    "employee_name": data["employee_name"],
                    "employee_email": email,
                    "grants_count": data["grants_count"],
                    "total_options": total,
                    "vested_options": vested,
                    "unvested_options": unvested,
                    "vesting_progress_percent": float(progress),
                }
            )

        # Sort by employee name
        employees.sort(key=lambda x: x["employee_name"])

        return Response(
            {
                "total_employees": len(employees),
                "employees": employees,
            }
        )


class EmployeeESOPDetailView(APIView):
    """API endpoint for Employee ESOP Details - shows summary, grants, and exercise history."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        employee_email = request.query_params.get("employee_email")

        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)
        if not employee_email:
            return Response({"detail": "employee_email is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        # Get all active grants for this employee
        grants = (
            ESOPGrant.objects.filter(
                company=company, employee_email=employee_email, status="Active"
            )
            .select_related("vesting_schedule_plan")
            .order_by("-grant_date")
        )

        if not grants.exists():
            return Response(
                {"detail": "No ESOP grants found for this employee"}, status=404
            )

        # Get employee name from first grant
        employee_name = grants.first().employee_name

        # Calculate summary metrics
        total_options = sum(grant.total_options for grant in grants)
        total_vested = Decimal("0")
        total_unvested = Decimal("0")

        grants_data = []
        for grant in grants:
            progress, vested, unvested = grant.calculate_vesting_metrics()
            total_vested += vested
            total_unvested += unvested

            grants_data.append(
                {
                    "id": str(grant.id),
                    "grant_date": grant.grant_date.isoformat(),
                    "total_options": grant.total_options,
                    "vested_options": int(vested),
                    "unvested_options": int(unvested),
                    "strike_price": str(grant.strike_price),
                    "status": grant.status,
                    "vesting_progress_percent": float(progress),
                }
            )

        vested_percentage = (
            (total_vested / Decimal(total_options) * Decimal("100")).quantize(
                Decimal("0.1")
            )
            if total_options > 0
            else Decimal("0")
        )

        # Exercisable options = vested options (for now, can be enhanced later)
        exercisable_options = int(total_vested)

        # Exercise history (placeholder for future implementation)
        exercise_history = []

        response_data = {
            "employee_name": employee_name,
            "employee_email": employee_email,
            "total_options": total_options,
            "grants_count": grants.count(),
            "total_vested_options": int(total_vested),
            "total_unvested_options": int(total_unvested),
            "vested_percentage": float(vested_percentage),
            "exercisable_options": exercisable_options,
            "total_exercised": 0,  # Placeholder
            "exercised_transactions_count": 0,  # Placeholder
            "grants": grants_data,
            "exercise_history": exercise_history,
        }

        return Response(response_data)


class CapitalStructureOverviewView(APIView):
    """API endpoint for Capital Structure Overview Dashboard."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        # Calculate ownership structure from capitalization table
        rows = CapitalizationTable.objects.filter(company=company).select_related(
            "shareholder"
        )

        total_issued_shares = Decimal("0")
        total_issued_amount = Decimal("0")
        ownership_by_type = {
            "Promoters/Founders": {"shares": Decimal("0"), "percentage": Decimal("0")},
            "Investors": {"shares": Decimal("0"), "percentage": Decimal("0")},
            "ESOP Pool": {"shares": Decimal("0"), "percentage": Decimal("0")},
            "Others": {"shares": Decimal("0"), "percentage": Decimal("0")},
        }

        for row in rows:
            shares = row.shares_issued or Decimal("0")
            amount = row.amount or Decimal("0")
            total_issued_shares += shares
            total_issued_amount += amount

            shareholder = row.shareholder
            if not shareholder:
                continue

            investor_type = shareholder.investor_type
            if investor_type == "Founder":
                ownership_by_type["Promoters/Founders"]["shares"] += shares
            elif investor_type in [
                "Angel Investor",
                "Venture Capital",
                "Strategic Investment",
            ]:
                ownership_by_type["Investors"]["shares"] += shares
            elif row.share_class_type == "ESOP":
                ownership_by_type["ESOP Pool"]["shares"] += shares
            else:
                ownership_by_type["Others"]["shares"] += shares

        # Calculate ESOP pool from grants (fully diluted)
        esop_grants = ESOPGrant.objects.filter(company=company, status="Active")
        total_granted_options = sum(grant.total_options for grant in esop_grants)

        # Use pool size from company or calculate from grants
        esop_pool_size = company.esop_pool_size or total_granted_options

        # Calculate fully diluted total (issued shares + ESOP pool)
        fully_diluted_total = total_issued_shares + Decimal(esop_pool_size)

        # Calculate percentages for fully diluted
        if fully_diluted_total > 0:
            for key in ownership_by_type:
                if key == "ESOP Pool":
                    # ESOP pool percentage is based on fully diluted
                    ownership_by_type[key]["percentage"] = (
                        (Decimal(esop_pool_size) / fully_diluted_total) * Decimal("100")
                    ).quantize(Decimal("0.1"))
                else:
                    # Other categories based on issued shares
                    ownership_by_type[key]["percentage"] = (
                        (ownership_by_type[key]["shares"] / fully_diluted_total)
                        * Decimal("100")
                    ).quantize(Decimal("0.1"))

        # Use company's issued capital if set, otherwise calculate from transactions
        issued_capital_shares = company.issued_capital_shares or int(
            total_issued_shares
        )
        issued_capital_amount = company.issued_capital_amount or total_issued_amount

        response_data = {
            "capital_structure": {
                "authorized_capital": {
                    "amount": str(company.authorized_capital_amount or Decimal("0")),
                    "shares": company.authorized_capital_shares or 0,
                },
                "issued_capital": {
                    "amount": str(issued_capital_amount),
                    "shares": issued_capital_shares,
                },
                "paid_up_capital": {
                    "amount": str(company.paid_up_capital_amount or Decimal("0")),
                    "shares": company.paid_up_capital_shares or 0,
                    "status": (
                        "Fully paid"
                        if (
                            company.paid_up_capital_amount
                            and company.issued_capital_amount
                            and company.paid_up_capital_amount
                            >= company.issued_capital_amount
                        )
                        else "Partially paid"
                    ),
                },
                "securities_premium": {
                    "amount": str(company.securities_premium or Decimal("0")),
                    "description": "Share premium account",
                },
            },
            "capital_utilization": {
                "percentage": float(company.capital_utilization_percentage),
                "authorized_amount": str(
                    company.authorized_capital_amount or Decimal("0")
                ),
                "issued_amount": str(issued_capital_amount),
                "available_amount": str(company.available_capital),
            },
            "ownership_structure_fully_diluted": [
                {
                    "category": key,
                    "shares": (
                        int(value["shares"]) if key != "ESOP Pool" else esop_pool_size
                    ),
                    "percentage": float(value["percentage"]),
                }
                for key, value in ownership_by_type.items()
            ],
            "total_shareholders_funds": {
                "formula": "Paid-up Capital + Securities Premium",
                "total_value": str(company.total_shareholders_funds),
            },
        }

        return Response(response_data)


class ESOPPoolOverviewView(APIView):
    """API endpoint for ESOP Pool Overview."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        # Calculate granted options from all active grants
        esop_grants = ESOPGrant.objects.filter(company=company, status="Active")
        total_granted = sum(grant.total_options for grant in esop_grants)

        # Calculate vested and unvested
        total_vested = Decimal("0")
        total_unvested = Decimal("0")

        for grant in esop_grants:
            _, vested, unvested = grant.calculate_vesting_metrics()
            total_vested += vested
            total_unvested += unvested

        # Pool size and percentage
        pool_size = company.esop_pool_size or 0
        pool_percentage = company.esop_pool_percentage or Decimal("0")
        authorized_shares = company.authorized_capital_shares or 0

        # Calculate utilization
        utilization_percentage = Decimal("0")
        if pool_size > 0:
            utilization_percentage = (
                Decimal(total_granted) / Decimal(pool_size)
            ) * Decimal("100")

        # Pool allocation description
        pool_allocation = (
            f"{pool_percentage}% of {authorized_shares:,} authorized shares"
        )
        if pool_percentage == 0 and pool_size > 0:
            pool_allocation = f"{pool_size:,} shares"

        response_data = {
            "pool_allocation": pool_allocation,
            "pool_size": pool_size,
            "granted": int(total_granted),
            "utilization": float(utilization_percentage.quantize(Decimal("0.1"))),
            "vested": int(total_vested),
            "unvested": int(total_unvested),
            "authorized_shares": authorized_shares,
            "pool_percentage": float(pool_percentage),
        }

        return Response(response_data)


class ConfigureESOPPoolView(APIView):
    """API endpoint to configure ESOP Pool."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        response_data = {
            "pool_percentage": float(company.esop_pool_percentage or Decimal("0")),
            "pool_size": company.esop_pool_size or 0,
            "authorized_shares": company.authorized_capital_shares or 0,
            "notes": company.esop_pool_notes or "",
        }

        return Response(response_data)

    def post(self, request, *args, **kwargs):
        company_id = request.data.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found"}, status=404)

        pool_percentage = request.data.get("pool_percentage")
        pool_size = request.data.get("pool_size")
        notes = request.data.get("notes", "")

        authorized_shares = company.authorized_capital_shares or 0

        if pool_percentage is not None and pool_size is not None:
            # Both provided - validate consistency
            calculated_size = int(
                (Decimal(pool_percentage) / Decimal("100")) * Decimal(authorized_shares)
            )
            if calculated_size != pool_size:
                return Response(
                    {
                        "detail": "Pool size and percentage are inconsistent with authorized shares"
                    },
                    status=400,
                )

        if pool_percentage is not None:
            pool_percentage = Decimal(str(pool_percentage))
            if pool_percentage < 0 or pool_percentage > 100:
                return Response(
                    {"detail": "Pool percentage must be between 0 and 100"}, status=400
                )
            # Calculate pool size from percentage
            if authorized_shares > 0:
                pool_size = int(
                    (pool_percentage / Decimal("100")) * Decimal(authorized_shares)
                )
            else:
                return Response(
                    {
                        "detail": "Authorized shares must be set before configuring ESOP pool"
                    },
                    status=400,
                )

        if pool_size is not None:
            pool_size = int(pool_size)
            if pool_size < 0:
                return Response({"detail": "Pool size cannot be negative"}, status=400)
            if authorized_shares > 0 and pool_size > authorized_shares:
                return Response(
                    {"detail": "Pool size cannot exceed authorized shares"}, status=400
                )
            # Calculate percentage from pool size
            if authorized_shares > 0:
                pool_percentage = (
                    Decimal(pool_size) / Decimal(authorized_shares)
                ) * Decimal("100")
            else:
                pool_percentage = Decimal("0")

        # Validate that total granted doesn't exceed new pool size
        if pool_size is not None:
            esop_grants = ESOPGrant.objects.filter(company=company, status="Active")
            total_granted = sum(grant.total_options for grant in esop_grants)
            if total_granted > pool_size:
                return Response(
                    {
                        "detail": f"Total granted options ({total_granted}) exceeds new pool size ({pool_size})"
                    },
                    status=400,
                )

        # Update company
        if pool_percentage is not None:
            company.esop_pool_percentage = pool_percentage
        if pool_size is not None:
            company.esop_pool_size = pool_size
        if notes is not None:
            company.esop_pool_notes = notes

        try:
            company.full_clean()
            company.updated_by = request.user
            company.save()
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        response_data = {
            "pool_percentage": float(company.esop_pool_percentage),
            "pool_size": company.esop_pool_size,
            "authorized_shares": company.authorized_capital_shares,
            "notes": company.esop_pool_notes or "",
        }

        return Response(response_data, status=status.HTTP_200_OK)
