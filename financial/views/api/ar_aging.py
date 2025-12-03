from decimal import Decimal

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.ar_aging import ARAgeingSummarySerializer


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


class ARAgeingSummaryView(APIView):
    """
    API view to get AR Ageing Summary dashboard data.

    Returns:
    - Total AR amount
    - AR breakdown by ageing buckets (Current, 1-30 Days, 31-60 Days, 61-90 Days, 90+ Days)
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
        Calculate which ageing bucket an invoice falls into based on when payment will be received.
        Based on due_date - when payment is expected to be received.
        """
        days_until_due = (due_date - today).days

        # Current: Payment due today
        if days_until_due == 0:
            return "current"
        # 1-30 Days: Payment will be received in 1-30 days
        elif days_until_due > 0 and days_until_due <= 30:
            return "1_30_days"
        # 31-60 Days: Payment will be received in 31-60 days
        elif days_until_due > 30 and days_until_due <= 60:
            return "31_60_days"
        # 61-90 Days: Payment will be received in 61-90 days
        elif days_until_due > 60 and days_until_due <= 90:
            return "61_90_days"
        # 90+ Days: Payment will be received in 90+ days OR overdue (past due date)
        else:
            return "90_plus_days"

    def _get_queryset(self, request):
        """Get filtered invoices queryset for the company"""
        company = get_company_from_request(request)
        if not company:
            return Invoice.objects.none()

        # Get all invoices with outstanding balance (not fully paid or cancelled)
        # Filter by calculated balance: total_amount > paid_amount
        queryset = (
            Invoice.objects.filter(company=company)
            .exclude(
                status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
            )
            .filter(total_amount__gt=F("paid_amount"))
        )

        return queryset

    def get(self, request, *args, **kwargs):
        """Calculate and return AR ageing summary"""
        invoices = self._get_queryset(request)

        if not invoices.exists():
            # Return empty response
            return Response(
                {
                    "total_ar": 0,
                    "total_ar_display": "₹0.00L",
                    "overdue_percentage": 0.0,
                    "portfolio_health": "No Outstanding AR",
                    "ageing_buckets": [],
                }
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
        for invoice in invoices:
            bucket = self._calculate_ageing_bucket(invoice.due_date, today)
            # Use balance_amount property (total - paid)
            balance = invoice.balance_amount
            buckets[bucket] += balance

        # Calculate total AR
        total_ar = sum(buckets.values())

        # Calculate overdue amount (all buckets except current)
        overdue_amount = total_ar - buckets["current"]
        overdue_percentage = (
            float((overdue_amount / total_ar * 100)) if total_ar > 0 else 0.0
        )

        # Determine portfolio health
        if overdue_percentage >= 70:
            portfolio_health = "At Risk - Prioritize collections"
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
                    float((buckets["current"] / total_ar * 100))
                    if total_ar > 0
                    else 0.0
                ),
            },
            {
                "label": "1-30 Days",
                "amount": float(buckets["1_30_days"]),
                "amount_display": self._in_lakhs(buckets["1_30_days"]),
                "percentage": (
                    float((buckets["1_30_days"] / total_ar * 100))
                    if total_ar > 0
                    else 0.0
                ),
            },
            {
                "label": "31-60 Days",
                "amount": float(buckets["31_60_days"]),
                "amount_display": self._in_lakhs(buckets["31_60_days"]),
                "percentage": (
                    float((buckets["31_60_days"] / total_ar * 100))
                    if total_ar > 0
                    else 0.0
                ),
            },
            {
                "label": "61-90 Days",
                "amount": float(buckets["61_90_days"]),
                "amount_display": self._in_lakhs(buckets["61_90_days"]),
                "percentage": (
                    float((buckets["61_90_days"] / total_ar * 100))
                    if total_ar > 0
                    else 0.0
                ),
            },
            {
                "label": "90+ Days",
                "amount": float(buckets["90_plus_days"]),
                "amount_display": self._in_lakhs(buckets["90_plus_days"]),
                "percentage": (
                    float((buckets["90_plus_days"] / total_ar * 100))
                    if total_ar > 0
                    else 0.0
                ),
            },
        ]

        response_data = {
            "total_ar": float(total_ar),
            "total_ar_display": self._in_lakhs(total_ar),
            "overdue_percentage": round(overdue_percentage, 1),
            "portfolio_health": portfolio_health,
            "ageing_buckets": ageing_buckets,
        }

        # Validate with serializer
        serializer = ARAgeingSummarySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
