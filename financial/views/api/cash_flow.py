from decimal import Decimal
from datetime import timedelta
from collections import defaultdict

from django.db.models import F, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.models.cash_flow import CashFlowProjection
from financial.enums import InvoicesStatusChoices
from financial.serializers.cash_flow import CashFlowProjectionSerializer
from financial.views.api.ar_aging import get_company_from_request


class CashFlowProjectionView(APIView):
    """Get cash flow projection data"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "summary": {
                    "next_30_days": 0,
                    "next_30_days_display": "₹0.00L",
                    "next_60_days": 0,
                    "next_60_days_display": "₹0.00L",
                    "next_90_days": 0,
                    "next_90_days_display": "₹0.00L",
                    "total_due": 0,
                    "total_due_display": "₹0.00L",
                },
                "projections": [],
                "risk_analysis": {
                    "collection_rate_assumption": "70% on-time, 20% delayed",
                    "high_risk_invoices": 0,
                    "expected_vs_total_due": "0%",
                }
            })

        projection_type = request.query_params.get("type", "weekly")  # weekly or monthly
        today = timezone.now().date()
        
        # Get all outstanding invoices
        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        # Calculate summary
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
        start_date = today
        
        if projection_type == "weekly":
            end_date = today + timedelta(days=90)
            delta = timedelta(days=7)
        else:  # monthly
            end_date = today + timedelta(days=180)
            delta = timedelta(days=30)

        current_date = start_date
        while current_date <= end_date:
            due_amount = Decimal("0")
            expected_collection = Decimal("0")
            optimistic_collection = Decimal("0")
            conservative_collection = Decimal("0")

            # Calculate amounts for this period
            period_end = current_date + delta if projection_type == "weekly" else current_date + timedelta(days=30)
            
            for invoice in invoices:
                if current_date <= invoice.due_date < period_end:
                    balance = invoice.balance_amount
                    due_amount += balance
                    
                    # Calculate expected collection (70% on-time, 20% delayed)
                    if invoice.due_date <= current_date + timedelta(days=7):
                        expected_collection += balance * Decimal("0.70")
                        optimistic_collection += balance * Decimal("0.85")
                        conservative_collection += balance * Decimal("0.60")
                    else:
                        expected_collection += balance * Decimal("0.20")
                        optimistic_collection += balance * Decimal("0.30")
                        conservative_collection += balance * Decimal("0.10")

            projections.append({
                "projection_date": current_date,
                "date_display": current_date.strftime("%b %d"),
                "due_amount": float(due_amount),
                "due_amount_display": self._in_lakhs(due_amount),
                "expected_collection": float(expected_collection),
                "expected_collection_display": self._in_lakhs(expected_collection),
                "optimistic_collection": float(optimistic_collection),
                "optimistic_collection_display": self._in_lakhs(optimistic_collection),
                "conservative_collection": float(conservative_collection),
                "conservative_collection_display": self._in_lakhs(conservative_collection),
            })

            current_date += delta

        # Risk Analysis
        high_risk_invoices = invoices.filter(
            due_date__lt=today - timedelta(days=60)
        ).count()

        expected_collection_total = total_due * Decimal("0.70")
        collection_rate = float((expected_collection_total / total_due * 100)) if total_due > 0 else 0.0

        return Response({
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
                "expected_vs_total_due": f"{collection_rate:.0f}%",
            }
        })

