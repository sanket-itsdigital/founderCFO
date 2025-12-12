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
    - Projections: Daily projection data with due amounts and cumulative amounts
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

    def get(self, request, *args, **kwargs):
        """Calculate and return AP cash flow projection data"""
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

        # Get all outstanding bills (not fully paid or cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED])
            .filter(amount__gt=F("paid_amount"))
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
            balance = bill.balance_amount
            due_date = bill.due_date

            # Add to summary buckets
            if due_date <= next_7_days:
                summary_7 += balance
            if due_date <= next_30_days:
                summary_30 += balance
            if due_date <= next_90_days:
                summary_90 += balance

            # Add to daily due amounts
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

            # Format date display
            date_display = current_date.strftime("%b %d")

            projections.append(
                {
                    "date": current_date,
                    "date_display": date_display,
                    "due_amount": float(due_amount),
                    "due_amount_display": (
                        self._in_lakhs(due_amount) if due_amount > 0 else "₹0.00L"
                    ),
                    "cumulative_amount": float(cumulative),
                    "cumulative_amount_display": (
                        self._in_lakhs(cumulative)
                        if cumulative < Decimal("10000000")
                        else self._in_crores(cumulative)
                    ),
                }
            )

            current_date += timedelta(days=1)

        response_data = {
            "summary": {
                "next_7_days": float(summary_7),
                "next_7_days_display": self._in_lakhs(summary_7),
                "next_30_days": float(summary_30),
                "next_30_days_display": self._in_lakhs(summary_30),
                "next_90_days": float(summary_90),
                "next_90_days_display": self._in_lakhs(summary_90),
            },
            "projections": projections,
        }

        serializer = CashFlowProjectionSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
