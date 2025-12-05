from decimal import Decimal

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_payable.bills import Bill
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.ap_aging import APAgeingSummarySerializer


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


class APAgeingSummaryView(APIView):
    """
    API view to get AP Ageing Summary dashboard data.

    Returns:
    - Total AP amount
    - AP breakdown by ageing buckets (Current, 1-30 Days, 31-60 Days, 61-90 Days, 90+ Days)
    - Overdue percentage
    - Portfolio health indicator
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _calculate_ageing_bucket(due_date, today):
        """
        Calculate which ageing bucket a bill falls into based on when payment is due.
        Based on due_date - when payment is expected to be made.
        """
        days_until_due = (due_date - today).days

        # Current: Payment due today or already overdue
        if days_until_due <= 0:
            return "current"
        # 1-30 Days: Payment will be due in 1-30 days
        elif days_until_due > 0 and days_until_due <= 30:
            return "1_30_days"
        # 31-60 Days: Payment will be due in 31-60 days
        elif days_until_due > 30 and days_until_due <= 60:
            return "31_60_days"
        # 61-90 Days: Payment will be due in 61-90 days
        elif days_until_due > 60 and days_until_due <= 90:
            return "61_90_days"
        # 90+ Days: Payment will be due in 90+ days
        else:
            return "90_plus_days"

    def _get_queryset(self, request):
        """Get filtered bills queryset for the company"""
        company = get_company_from_request(request)
        if not company:
            return Bill.objects.none()

        # Get all bills with outstanding balance (not fully paid or cancelled)
        # Filter by calculated balance: amount > paid_amount
        queryset = (
            Bill.objects.filter(company=company)
            .exclude(
                status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED]
            )
            .filter(amount__gt=F("paid_amount"))
        )

        return queryset

    def get(self, request, *args, **kwargs):
        """Calculate and return AP ageing summary"""
        bills = self._get_queryset(request)

        if not bills.exists():
            # Return empty response
            return Response(
                {
                    "total_ap": 0,
                    "total_ap_display": "₹0.00L",
                    "overdue_percentage": 0.0,
                    "portfolio_health": "No Outstanding AP",
                    "ageing_buckets": [],
                },
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()

        # Initialize bucket totals
        buckets = {
            "current": Decimal("0"),
            "1_30_days": Decimal("0"),
            "31_60_days": Decimal("0"),
            "61_90_days": Decimal("0"),
            "90_plus_days": Decimal("0"),
        }

        # Calculate amounts for each bucket
        for bill in bills:
            bucket = self._calculate_ageing_bucket(bill.due_date, today)
            # Use balance_amount property (amount - paid_amount)
            balance = bill.balance_amount
            buckets[bucket] += balance

        # Calculate total AP
        total_ap = sum(buckets.values())

        # Calculate overdue amount (current bucket includes overdue bills)
        # Overdue = bills where due_date < today
        overdue_amount = Decimal("0")
        for bill in bills:
            if bill.due_date < today:
                overdue_amount += bill.balance_amount

        overdue_percentage = (
            float((overdue_amount / total_ap * 100)) if total_ap > 0 else 0.0
        )

        # Determine portfolio health
        if overdue_percentage >= 70:
            portfolio_health = "At Risk - Prioritize payments"
        elif overdue_percentage >= 50:
            portfolio_health = "Moderate Risk - Monitor closely"
        elif overdue_percentage >= 30:
            portfolio_health = "Low Risk - Standard monitoring"
        else:
            portfolio_health = "Healthy - Minimal risk"

        # Format ageing buckets data
        ageing_buckets = [
            {
                "label": "Current",
                "amount": float(buckets["current"]),
                "amount_display": self._in_lakhs(buckets["current"]),
                "percentage": (
                    float((buckets["current"] / total_ap * 100))
                    if total_ap > 0
                    else 0.0
                ),
            },
            {
                "label": "1-30 Days",
                "amount": float(buckets["1_30_days"]),
                "amount_display": self._in_lakhs(buckets["1_30_days"]),
                "percentage": (
                    float((buckets["1_30_days"] / total_ap * 100))
                    if total_ap > 0
                    else 0.0
                ),
            },
            {
                "label": "31-60 Days",
                "amount": float(buckets["31_60_days"]),
                "amount_display": self._in_lakhs(buckets["31_60_days"]),
                "percentage": (
                    float((buckets["31_60_days"] / total_ap * 100))
                    if total_ap > 0
                    else 0.0
                ),
            },
            {
                "label": "61-90 Days",
                "amount": float(buckets["61_90_days"]),
                "amount_display": self._in_lakhs(buckets["61_90_days"]),
                "percentage": (
                    float((buckets["61_90_days"] / total_ap * 100))
                    if total_ap > 0
                    else 0.0
                ),
            },
            {
                "label": "90+ Days",
                "amount": float(buckets["90_plus_days"]),
                "amount_display": self._in_lakhs(buckets["90_plus_days"]),
                "percentage": (
                    float((buckets["90_plus_days"] / total_ap * 100))
                    if total_ap > 0
                    else 0.0
                ),
            },
        ]

        response_data = {
            "total_ap": float(total_ap),
            "total_ap_display": self._in_lakhs(total_ap),
            "overdue_percentage": round(overdue_percentage, 1),
            "portfolio_health": portfolio_health,
            "ageing_buckets": ageing_buckets,
        }

        # Validate with serializer
        serializer = APAgeingSummarySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

