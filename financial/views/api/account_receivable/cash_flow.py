from decimal import Decimal
from datetime import timedelta
from collections import defaultdict

from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.account_receivable.cash_flow import CashFlowProjectionResponseSerializer
from financial.views.api.account_receivable.ar_aging import get_company_from_request


class CashFlowProjectionView(APIView):
    """
    Get cash flow projection data with weekly/monthly projections.
    
    Returns:
    - Summary: Next 30/60/90 days and total due amounts
    - Projections: Weekly or monthly projection data with due amounts and collection estimates
    - Risk Analysis: Collection assumptions, high-risk invoices, and expected collection rate
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _calculate_collection_estimates(self, balance, days_until_due):
        """
        Calculate collection estimates based on days until due date.
        Assumption: 70% on-time (within 7 days of due), 20% delayed (after 7 days)
        """
        if days_until_due <= 7:
            # On-time collection
            expected = balance * Decimal("0.70")
            optimistic = balance * Decimal("0.85")
            conservative = balance * Decimal("0.60")
        elif days_until_due <= 14:
            # Slightly delayed
            expected = balance * Decimal("0.50")
            optimistic = balance * Decimal("0.70")
            conservative = balance * Decimal("0.40")
        else:
            # Delayed collection
            expected = balance * Decimal("0.20")
            optimistic = balance * Decimal("0.30")
            conservative = balance * Decimal("0.10")
        
        return expected, optimistic, conservative

    def get(self, request, *args, **kwargs):
        """Calculate and return cash flow projection data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "next_30_days": 0.0,
                        "next_30_days_display": "₹0.00L",
                        "next_60_days": 0.0,
                        "next_60_days_display": "₹0.00L",
                        "next_90_days": 0.0,
                        "next_90_days_display": "₹0.00L",
                        "total_due": 0.0,
                        "total_due_display": "₹0.00L",
                    },
                    "projections": [],
                    "risk_analysis": {
                        "collection_rate_assumption": "70% on-time, 20% delayed",
                        "high_risk_invoices": 0,
                        "high_risk_invoices_display": "0 invoices",
                        "expected_vs_total_due": "0%",
                    },
                    "projection_type": "weekly",
                },
                status=status.HTTP_200_OK,
            )

        projection_type = request.query_params.get("type", "weekly")  # weekly or monthly
        today = timezone.now().date()
        
        # Get all outstanding invoices (not paid or cancelled)
        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F("paid_amount")
        )

        # Calculate summary amounts
        next_30_days = today + timedelta(days=30)
        next_60_days = today + timedelta(days=60)
        next_90_days = today + timedelta(days=90)

        summary_30 = Decimal("0")
        summary_60 = Decimal("0")
        summary_90 = Decimal("0")
        total_due = Decimal("0")

        for invoice in invoices:
            balance = invoice.balance_amount
            total_due += balance
            
            if invoice.due_date <= next_30_days:
                summary_30 += balance
            if invoice.due_date <= next_60_days:
                summary_60 += balance
            if invoice.due_date <= next_90_days:
                summary_90 += balance

        # Generate projections
        projections = []
        
        if projection_type == "weekly":
            # Weekly projections for next 12 weeks (~90 days)
            num_weeks = 12
            
            # Initialize weekly buckets
            weekly_due = defaultdict(lambda: Decimal("0"))
            weekly_expected_collection = defaultdict(lambda: Decimal("0"))
            weekly_optimistic_collection = defaultdict(lambda: Decimal("0"))
            weekly_conservative_collection = defaultdict(lambda: Decimal("0"))
            
            # Process each invoice
            for invoice in invoices:
                balance = invoice.balance_amount
                days_until_due = (invoice.due_date - today).days
                
                # Determine which week the invoice is due
                due_week = days_until_due // 7
                if 0 <= due_week < num_weeks:
                    weekly_due[due_week] += balance
                    
                    # Project collections: 70% on-time (1 week after due), 20% delayed (2-3 weeks)
                    # On-time collection (70% of amount) in week after due
                    collection_week = due_week + 1
                    if collection_week < num_weeks:
                        weekly_expected_collection[collection_week] += balance * Decimal("0.70")
                        weekly_optimistic_collection[collection_week] += balance * Decimal("0.85")
                        weekly_conservative_collection[collection_week] += balance * Decimal("0.60")
                    
                    # Delayed collection (20% of amount) in 2-3 weeks after due
                    delayed_week = due_week + 2
                    if delayed_week < num_weeks:
                        weekly_expected_collection[delayed_week] += balance * Decimal("0.20")
                        weekly_optimistic_collection[delayed_week] += balance * Decimal("0.30")
                        weekly_conservative_collection[delayed_week] += balance * Decimal("0.10")
            
            # Build projections array
            for week in range(num_weeks):
                week_start = today + timedelta(weeks=week)
                
                due_amount = weekly_due.get(week, Decimal("0"))
                expected_collection = weekly_expected_collection.get(week, Decimal("0"))
                optimistic_collection = weekly_optimistic_collection.get(week, Decimal("0"))
                conservative_collection = weekly_conservative_collection.get(week, Decimal("0"))
                
                # Format date display
                date_display = week_start.strftime("%b %d")
                
                projections.append({
                    "projection_date": week_start,
                    "date_display": date_display,
                    "due_amount": float(due_amount),
                    "due_amount_display": self._in_lakhs(due_amount),
                    "expected_collection": float(expected_collection),
                    "expected_collection_display": self._in_lakhs(expected_collection),
                    "optimistic_collection": float(optimistic_collection),
                    "optimistic_collection_display": self._in_lakhs(optimistic_collection),
                    "conservative_collection": float(conservative_collection),
                    "conservative_collection_display": self._in_lakhs(conservative_collection),
                })
        else:
            # Monthly projections for next 6 months
            num_months = 6
            for month in range(num_months):
                month_start = today.replace(day=1) + timedelta(days=32 * month)
                month_start = month_start.replace(day=1)
                
                # Calculate month end
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
                
                due_amount = Decimal("0")
                expected_collection = Decimal("0")
                optimistic_collection = Decimal("0")
                conservative_collection = Decimal("0")
                
                # Calculate amounts for invoices due in this month
                for invoice in invoices:
                    if month_start <= invoice.due_date <= month_end:
                        balance = invoice.balance_amount
                        due_amount += balance
                        
                        days_until_due = (invoice.due_date - today).days
                        expected, optimistic, conservative = self._calculate_collection_estimates(
                            balance, days_until_due
                        )
                        
                        # Collections typically happen in the same month or next month
                        expected_collection += expected
                        optimistic_collection += optimistic
                        conservative_collection += conservative
                
                date_display = month_start.strftime("%b %Y")
                
                projections.append({
                    "projection_date": month_start,
                    "date_display": date_display,
                    "due_amount": float(due_amount),
                    "due_amount_display": self._in_lakhs(due_amount),
                    "expected_collection": float(expected_collection),
                    "expected_collection_display": self._in_lakhs(expected_collection),
                    "optimistic_collection": float(optimistic_collection),
                    "optimistic_collection_display": self._in_lakhs(optimistic_collection),
                    "conservative_collection": float(conservative_collection),
                    "conservative_collection_display": self._in_lakhs(conservative_collection),
                })

        # Risk Analysis
        # High-risk invoices: 60+ days overdue
        high_risk_invoices = invoices.filter(
            due_date__lt=today - timedelta(days=60)
        ).count()
        
        # Calculate expected collection rate
        expected_collection_total = total_due * Decimal("0.70")  # 70% collection rate assumption
        collection_rate = (
            float((expected_collection_total / total_due * 100))
            if total_due > 0
            else 0.0
        )

        response_data = {
            "summary": {
                "next_30_days": float(summary_30),
                "next_30_days_display": self._in_lakhs(summary_30),
                "next_60_days": float(summary_60),
                "next_60_days_display": self._in_lakhs(summary_60),
                "next_90_days": float(summary_90),
                "next_90_days_display": self._in_lakhs(summary_90),
                "total_due": float(total_due),
                "total_due_display": self._in_lakhs(total_due),
            },
            "projections": projections,
            "risk_analysis": {
                "collection_rate_assumption": "70% on-time, 20% delayed",
                "high_risk_invoices": high_risk_invoices,
                "high_risk_invoices_display": f"{high_risk_invoices} invoices (60+ days overdue)",
                "expected_vs_total_due": f"{collection_rate:.0f}% collection rate",
            },
            "projection_type": projection_type,
        }

        # Validate with serializer
        serializer = CashFlowProjectionResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
