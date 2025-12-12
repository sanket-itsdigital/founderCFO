from decimal import Decimal
from datetime import timedelta
from collections import defaultdict

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.cash_flow_projection import (
    CashFlowProjectionSerializer,
)
from financial.views.api.account_payable.ap_aging import get_company_from_request


class APCashFlowProjectionView(APIView):
    """
    Get AP cash flow projection data.

    Returns:
    - Summary: Next 7/30/90 days projected outflows
    - Projections: Daily projection data with due amounts (for line chart) and cumulative amounts (for area chart)

    All data comes from the Bill model (expenses.bills).
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
    def _in_crores(amount: Decimal) -> str:
        """Convert amount to crores format (₹XX.XXCr)"""
        if amount == 0:
            return "₹0.00Cr"
        crores = amount / Decimal("10000000")
        return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as L or Cr based on value"""
        if amount >= Decimal("10000000"):  # 1 Crore
            return APCashFlowProjectionView._in_crores(amount)
        else:
            return APCashFlowProjectionView._in_lakhs(amount)

    def get(self, request, *args, **kwargs):
        """Calculate and return AP cash flow projection data - all from Bill model"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "next_7_days": 0.0,
                        "next_7_days_display": "₹0.00L",
                        "next_30_days": 0.0,
                        "next_30_days_display": "₹0.00L",
                        "next_90_days": 0.0,
                        "next_90_days_display": "₹0.00L",
                    },
                    "projections": [],
                },
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()

        # Get all outstanding bills from Bill model (not fully paid or cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED])
            .filter(total__gt=F("paid_amount"))  # Use total instead of amount
            .select_related("vendor")
        )

        # Calculate summary amounts
        next_7_days = today + timedelta(days=7)
        next_30_days = today + timedelta(days=30)
        next_90_days = today + timedelta(days=90)

        summary_7 = Decimal("0")
        summary_30 = Decimal("0")
        summary_90 = Decimal("0")

        # Group bills by due date for daily projections
        daily_due = defaultdict(lambda: Decimal("0"))

        for bill in bills:
            # Get balance from Bill model
            balance = bill.balance_amount  # Uses total - paid_amount
            due_date = bill.due_date

            if not due_date:
                continue

            # Add to summary buckets (bills due on or before the date)
            if due_date <= next_7_days:
                summary_7 += balance
            if due_date <= next_30_days:
                summary_30 += balance
            if due_date <= next_90_days:
                summary_90 += balance

            # Add to daily due amounts (only future dates within projection window)
            if due_date >= today and due_date <= next_90_days:
                daily_due[due_date] += balance

        # Generate daily projections for next 90 days
        projections = []
        cumulative = Decimal("0")

        current_date = today
        end_date = next_90_days

        while current_date <= end_date:
            due_amount = daily_due.get(current_date, Decimal("0"))
            cumulative += due_amount

            # Format date display: "Dec 12", "Jan 11", etc.
            date_display = current_date.strftime("%b %d")

            projections.append(
                {
                    "date": current_date,
                    "date_display": date_display,
                    "due_amount": float(due_amount),
                    "due_amount_display": (
                        self._format_amount_display(due_amount)
                        if due_amount > 0
                        else "₹0"
                    ),
                    "cumulative_amount": float(cumulative),
                    "cumulative_amount_display": self._format_amount_display(
                        cumulative
                    ),
                }
            )

            current_date += timedelta(days=1)

        response_data = {
            "summary": {
                "next_7_days": float(summary_7),
                "next_7_days_display": self._format_amount_display(summary_7),
                "next_30_days": float(summary_30),
                "next_30_days_display": self._format_amount_display(summary_30),
                "next_90_days": float(summary_90),
                "next_90_days_display": self._format_amount_display(summary_90),
            },
            "projections": projections,
        }

        serializer = CashFlowProjectionSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
