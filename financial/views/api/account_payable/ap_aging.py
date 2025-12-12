from decimal import Decimal
from collections import defaultdict

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.expenses.bills import Bill
from financial.enums import BillsStatusChoices, RiskLevelChoices
from financial.serializers.account_payable.ap_aging import (
    APAgeingOverviewSerializer,
    APAgeingByVendorSerializer,
    APAgeingByCategorySerializer,
    APAgeingByStatusSerializer,
)


def get_company_from_request(request):
    """Helper function to get company from request"""
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return None
    # Try to get the first company owned by the user
    return Company.objects.filter(owner=request.user).first()


class APAgeingBaseView(APIView):
    """Base view with shared methods for AP Ageing views"""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0"
        lakhs = amount / Decimal("100000")
        if lakhs < 1:
            # For amounts less than 1 lakh, show in thousands
            thousands = amount / Decimal("1000")
            return f"₹{thousands.quantize(Decimal('0.1'))}K"
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _calculate_ageing_bucket(due_date, today):
        """
        Calculate which ageing bucket a bill falls into.
        - Current: Not overdue (due_date >= today)
        - 1-30 Days: Overdue by 1-30 days
        - 31-60 Days: Overdue by 31-60 days
        - 61-90 Days: Overdue by 61-90 days
        - 90+ Days: Overdue by 90+ days
        """
        if due_date >= today:
            return "current"

        days_overdue = (today - due_date).days

        if days_overdue <= 30:
            return "overdue_1_30"
        elif days_overdue <= 60:
            return "overdue_31_60"
        elif days_overdue <= 90:
            return "overdue_61_90"
        else:
            return "overdue_90_plus"

    @staticmethod
    def _calculate_risk_level(buckets, total):
        """Calculate risk level based on overdue amounts"""
        if total == 0:
            return RiskLevelChoices.LOW.value

        overdue_total = (
            buckets.get("overdue_1_30", Decimal("0"))
            + buckets.get("overdue_31_60", Decimal("0"))
            + buckets.get("overdue_61_90", Decimal("0"))
            + buckets.get("overdue_90_plus", Decimal("0"))
        )

        overdue_percentage = (overdue_total / total * 100) if total > 0 else 0

        if overdue_percentage >= 50 or buckets.get("overdue_90_plus", Decimal("0")) > 0:
            return RiskLevelChoices.HIGH.value
        elif overdue_percentage >= 30:
            return RiskLevelChoices.MEDIUM.value
        else:
            return RiskLevelChoices.LOW.value

    def _get_queryset(self, request):
        """Get filtered bills queryset for the company"""
        company = get_company_from_request(request)
        if not company:
            return Bill.objects.none()

        # Get all bills with outstanding balance (not fully paid or cancelled)
        queryset = (
            Bill.objects.filter(company=company)
            .exclude(status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED])
            .select_related("vendor")
        )

        # Filter by balance > 0 (total - paid_amount > 0)
        queryset = queryset.filter(total__gt=F("paid_amount"))

        return queryset


class APAgeingOverviewView(APAgeingBaseView):
    """
    API view to get AP Ageing Overview.

    Returns ageing buckets with amounts and percentages.
    """

    def get(self, request, *args, **kwargs):
        """Calculate and return AP ageing overview"""
        bills = self._get_queryset(request)

        if not bills.exists():
            return Response(
                {"ageing_buckets": []},
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()

        buckets = {
            "current": Decimal("0"),
            "overdue_1_30": Decimal("0"),
            "overdue_31_60": Decimal("0"),
            "overdue_61_90": Decimal("0"),
            "overdue_90_plus": Decimal("0"),
        }

        for bill in bills:
            bucket = self._calculate_ageing_bucket(bill.due_date, today)
            balance = bill.balance_amount
            buckets[bucket] += balance

        total = sum(buckets.values())

        ageing_buckets = [
            {
                "label": "Current",
                "amount": float(buckets["current"]),
                "amount_display": self._in_lakhs(buckets["current"]),
                "percentage": (
                    float((buckets["current"] / total * 100)) if total > 0 else 0.0
                ),
            },
            {
                "label": "1-30 Days",
                "amount": float(buckets["overdue_1_30"]),
                "amount_display": self._in_lakhs(buckets["overdue_1_30"]),
                "percentage": (
                    float((buckets["overdue_1_30"] / total * 100)) if total > 0 else 0.0
                ),
            },
            {
                "label": "31-60 Days",
                "amount": float(buckets["overdue_31_60"]),
                "amount_display": self._in_lakhs(buckets["overdue_31_60"]),
                "percentage": (
                    float((buckets["overdue_31_60"] / total * 100))
                    if total > 0
                    else 0.0
                ),
            },
            {
                "label": "61-90 Days",
                "amount": float(buckets["overdue_61_90"]),
                "amount_display": self._in_lakhs(buckets["overdue_61_90"]),
                "percentage": (
                    float((buckets["overdue_61_90"] / total * 100))
                    if total > 0
                    else 0.0
                ),
            },
            {
                "label": "90+ Days",
                "amount": float(buckets["overdue_90_plus"]),
                "amount_display": self._in_lakhs(buckets["overdue_90_plus"]),
                "percentage": (
                    float((buckets["overdue_90_plus"] / total * 100))
                    if total > 0
                    else 0.0
                ),
            },
        ]

        response_data = {"ageing_buckets": ageing_buckets}
        serializer = APAgeingOverviewSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class APAgeingByVendorView(APAgeingBaseView):
    """
    API view to get AP Ageing grouped by Vendor.

    Returns vendors with ageing buckets, risk levels, and bill details.
    """

    def get(self, request, *args, **kwargs):
        """Calculate and return AP ageing by vendor"""
        bills = self._get_queryset(request)
        today = timezone.now().date()

        if not bills.exists():
            return Response(
                {"vendors": [], "totals": {}},
                status=status.HTTP_200_OK,
            )

        vendor_data = defaultdict(
            lambda: {
                "vendor_id": None,
                "vendor_name": None,
                "buckets": {
                    "current": Decimal("0"),
                    "overdue_1_30": Decimal("0"),
                    "overdue_31_60": Decimal("0"),
                    "overdue_61_90": Decimal("0"),
                    "overdue_90_plus": Decimal("0"),
                },
                "bills": [],
            }
        )

        for bill in bills:
            vendor_key = (
                bill.vendor_id if bill.vendor else bill.vendor_name or "Unknown"
            )
            vendor_name = bill.get_vendor_name()

            if bill.vendor:
                vendor_data[vendor_key]["vendor_id"] = str(bill.vendor.id)
            vendor_data[vendor_key]["vendor_name"] = vendor_name

            bucket = self._calculate_ageing_bucket(bill.due_date, today)
            balance = bill.balance_amount
            vendor_data[vendor_key]["buckets"][bucket] += balance

            vendor_data[vendor_key]["bills"].append(
                {
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "vendor_name": vendor_name,
                    "due_date": bill.due_date,
                    "category": bill.category or "",
                    "amount": float(balance),
                    "amount_display": self._in_lakhs(balance),
                    "status": bill.status,
                }
            )

        vendors = []
        totals = {
            "current": Decimal("0"),
            "overdue_1_30": Decimal("0"),
            "overdue_31_60": Decimal("0"),
            "overdue_61_90": Decimal("0"),
            "overdue_90_plus": Decimal("0"),
        }

        for vendor_key, data in vendor_data.items():
            buckets = data["buckets"]
            total = sum(buckets.values())

            # Update totals
            for key in totals:
                totals[key] += buckets[key]

            risk_level = self._calculate_risk_level(buckets, total)

            vendors.append(
                {
                    "vendor_id": data["vendor_id"],
                    "vendor_name": data["vendor_name"],
                    "current_amount": float(buckets["current"]),
                    "current_amount_display": self._in_lakhs(buckets["current"]),
                    "overdue_1_30_amount": float(buckets["overdue_1_30"]),
                    "overdue_1_30_amount_display": self._in_lakhs(
                        buckets["overdue_1_30"]
                    ),
                    "overdue_31_60_amount": float(buckets["overdue_31_60"]),
                    "overdue_31_60_amount_display": self._in_lakhs(
                        buckets["overdue_31_60"]
                    ),
                    "overdue_61_90_amount": float(buckets["overdue_61_90"]),
                    "overdue_61_90_amount_display": self._in_lakhs(
                        buckets["overdue_61_90"]
                    ),
                    "overdue_90_plus_amount": float(buckets["overdue_90_plus"]),
                    "overdue_90_plus_amount_display": self._in_lakhs(
                        buckets["overdue_90_plus"]
                    ),
                    "total_amount": float(total),
                    "total_amount_display": self._in_lakhs(total),
                    "risk_level": risk_level,
                    "bills": data["bills"],
                }
            )

        # Sort by total amount descending
        vendors.sort(key=lambda x: x["total_amount"], reverse=True)

        response_data = {
            "vendors": vendors,
            "totals": {
                "current": float(totals["current"]),
                "current_display": self._in_lakhs(totals["current"]),
                "overdue_1_30": float(totals["overdue_1_30"]),
                "overdue_1_30_display": self._in_lakhs(totals["overdue_1_30"]),
                "overdue_31_60": float(totals["overdue_31_60"]),
                "overdue_31_60_display": self._in_lakhs(totals["overdue_31_60"]),
                "overdue_61_90": float(totals["overdue_61_90"]),
                "overdue_61_90_display": self._in_lakhs(totals["overdue_61_90"]),
                "overdue_90_plus": float(totals["overdue_90_plus"]),
                "overdue_90_plus_display": self._in_lakhs(totals["overdue_90_plus"]),
                "total": float(sum(totals.values())),
                "total_display": self._in_lakhs(sum(totals.values())),
            },
        }

        serializer = APAgeingByVendorSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class APAgeingByCategoryView(APAgeingBaseView):
    """
    API view to get AP Ageing grouped by Category.

    Returns categories with ageing buckets and bill details.
    """

    def get(self, request, *args, **kwargs):
        """Calculate and return AP ageing by category"""
        bills = self._get_queryset(request)
        today = timezone.now().date()

        if not bills.exists():
            return Response(
                {"categories": [], "totals": {}},
                status=status.HTTP_200_OK,
            )

        category_data = defaultdict(
            lambda: {
                "buckets": {
                    "current": Decimal("0"),
                    "overdue_1_30": Decimal("0"),
                    "overdue_31_60": Decimal("0"),
                    "overdue_61_90": Decimal("0"),
                    "overdue_90_plus": Decimal("0"),
                },
                "bills": [],
            }
        )

        for bill in bills:
            category = bill.category or "Uncategorized"
            bucket = self._calculate_ageing_bucket(bill.due_date, today)
            balance = bill.balance_amount
            category_data[category]["buckets"][bucket] += balance

            category_data[category]["bills"].append(
                {
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "vendor_name": bill.get_vendor_name(),
                    "due_date": bill.due_date,
                    "category": category,
                    "amount": float(balance),
                    "amount_display": self._in_lakhs(balance),
                    "status": bill.status,
                }
            )

        categories = []
        totals = {
            "current": Decimal("0"),
            "overdue_1_30": Decimal("0"),
            "overdue_31_60": Decimal("0"),
            "overdue_61_90": Decimal("0"),
            "overdue_90_plus": Decimal("0"),
        }

        for category, data in category_data.items():
            buckets = data["buckets"]
            total = sum(buckets.values())

            # Update totals
            for key in totals:
                totals[key] += buckets[key]

            categories.append(
                {
                    "category": category,
                    "current_amount": float(buckets["current"]),
                    "current_amount_display": self._in_lakhs(buckets["current"]),
                    "overdue_1_30_amount": float(buckets["overdue_1_30"]),
                    "overdue_1_30_amount_display": self._in_lakhs(
                        buckets["overdue_1_30"]
                    ),
                    "overdue_31_60_amount": float(buckets["overdue_31_60"]),
                    "overdue_31_60_amount_display": self._in_lakhs(
                        buckets["overdue_31_60"]
                    ),
                    "overdue_61_90_amount": float(buckets["overdue_61_90"]),
                    "overdue_61_90_amount_display": self._in_lakhs(
                        buckets["overdue_61_90"]
                    ),
                    "overdue_90_plus_amount": float(buckets["overdue_90_plus"]),
                    "overdue_90_plus_amount_display": self._in_lakhs(
                        buckets["overdue_90_plus"]
                    ),
                    "total_amount": float(total),
                    "total_amount_display": self._in_lakhs(total),
                    "bills": data["bills"],
                }
            )

        # Sort by total amount descending
        categories.sort(key=lambda x: x["total_amount"], reverse=True)

        response_data = {
            "categories": categories,
            "totals": {
                "current": float(totals["current"]),
                "current_display": self._in_lakhs(totals["current"]),
                "overdue_1_30": float(totals["overdue_1_30"]),
                "overdue_1_30_display": self._in_lakhs(totals["overdue_1_30"]),
                "overdue_31_60": float(totals["overdue_31_60"]),
                "overdue_31_60_display": self._in_lakhs(totals["overdue_31_60"]),
                "overdue_61_90": float(totals["overdue_61_90"]),
                "overdue_61_90_display": self._in_lakhs(totals["overdue_61_90"]),
                "overdue_90_plus": float(totals["overdue_90_plus"]),
                "overdue_90_plus_display": self._in_lakhs(totals["overdue_90_plus"]),
                "total": float(sum(totals.values())),
                "total_display": self._in_lakhs(sum(totals.values())),
            },
        }

        serializer = APAgeingByCategorySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class APAgeingByStatusView(APAgeingBaseView):
    """
    API view to get AP Ageing grouped by Status.

    Returns statuses with ageing buckets and bill details.
    """

    def get(self, request, *args, **kwargs):
        """Calculate and return AP ageing by status"""
        bills = self._get_queryset(request)
        today = timezone.now().date()

        if not bills.exists():
            return Response(
                {"statuses": [], "totals": {}},
                status=status.HTTP_200_OK,
            )

        status_data = defaultdict(
            lambda: {
                "buckets": {
                    "current": Decimal("0"),
                    "overdue_1_30": Decimal("0"),
                    "overdue_31_60": Decimal("0"),
                    "overdue_61_90": Decimal("0"),
                    "overdue_90_plus": Decimal("0"),
                },
                "bills": [],
            }
        )

        for bill in bills:
            bill_status = bill.status
            bucket = self._calculate_ageing_bucket(bill.due_date, today)
            balance = bill.balance_amount
            status_data[bill_status]["buckets"][bucket] += balance

            status_data[bill_status]["bills"].append(
                {
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "vendor_name": bill.get_vendor_name(),
                    "due_date": bill.due_date,
                    "category": bill.category or "",
                    "amount": float(balance),
                    "amount_display": self._in_lakhs(balance),
                    "status": bill_status,
                }
            )

        statuses = []
        totals = {
            "current": Decimal("0"),
            "overdue_1_30": Decimal("0"),
            "overdue_31_60": Decimal("0"),
            "overdue_61_90": Decimal("0"),
            "overdue_90_plus": Decimal("0"),
        }

        for bill_status, data in status_data.items():
            buckets = data["buckets"]
            total = sum(buckets.values())

            # Update totals
            for key in totals:
                totals[key] += buckets[key]

            statuses.append(
                {
                    "status": bill_status,
                    "current_amount": float(buckets["current"]),
                    "current_amount_display": self._in_lakhs(buckets["current"]),
                    "overdue_1_30_amount": float(buckets["overdue_1_30"]),
                    "overdue_1_30_amount_display": self._in_lakhs(
                        buckets["overdue_1_30"]
                    ),
                    "overdue_31_60_amount": float(buckets["overdue_31_60"]),
                    "overdue_31_60_amount_display": self._in_lakhs(
                        buckets["overdue_31_60"]
                    ),
                    "overdue_61_90_amount": float(buckets["overdue_61_90"]),
                    "overdue_61_90_amount_display": self._in_lakhs(
                        buckets["overdue_61_90"]
                    ),
                    "overdue_90_plus_amount": float(buckets["overdue_90_plus"]),
                    "overdue_90_plus_amount_display": self._in_lakhs(
                        buckets["overdue_90_plus"]
                    ),
                    "total_amount": float(total),
                    "total_amount_display": self._in_lakhs(total),
                    "bills": data["bills"],
                }
            )

        # Sort by status order: Pending, Partial, Overdue
        status_order = {
            BillsStatusChoices.PENDING: 1,
            BillsStatusChoices.PARTIAL: 2,
            BillsStatusChoices.OVERDUE: 3,
        }
        statuses.sort(key=lambda x: status_order.get(x["status"], 99))

        response_data = {
            "statuses": statuses,
            "totals": {
                "current": float(totals["current"]),
                "current_display": self._in_lakhs(totals["current"]),
                "overdue_1_30": float(totals["overdue_1_30"]),
                "overdue_1_30_display": self._in_lakhs(totals["overdue_1_30"]),
                "overdue_31_60": float(totals["overdue_31_60"]),
                "overdue_31_60_display": self._in_lakhs(totals["overdue_31_60"]),
                "overdue_61_90": float(totals["overdue_61_90"]),
                "overdue_61_90_display": self._in_lakhs(totals["overdue_61_90"]),
                "overdue_90_plus": float(totals["overdue_90_plus"]),
                "overdue_90_plus_display": self._in_lakhs(totals["overdue_90_plus"]),
                "total": float(sum(totals.values())),
                "total_display": self._in_lakhs(sum(totals.values())),
            },
        }

        serializer = APAgeingByStatusSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
