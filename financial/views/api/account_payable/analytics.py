from decimal import Decimal
from datetime import timedelta
from collections import defaultdict
from calendar import monthrange

from django.db.models import Sum, F, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.models.account_payable.payment import BillPayment, PaymentMethodChoices
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.analytics import APAnalyticsSerializer
from financial.views.api.account_payable.ap_aging import get_company_from_request


class APAnalyticsView(APIView):
    """
    Get all analytics data for AP reports.

    Returns:
    - Spending by Category: Pie chart data
    - Monthly Trend: Billed vs Paid over last 6 months
    - Top Vendors: Top 5 vendors by spending
    - Payment Methods: Distribution of payment methods
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

    def _calculate_spending_by_category(self, all_bills):
        """Calculate spending by category"""
        category_totals = defaultdict(Decimal)

        # Color mapping for categories
        category_colors = {
            "Office Supplies": "#3B82F6",  # Blue
            "Vehicle Fleet": "#10B981",  # Green
            "Maintenance": "#F59E0B",  # Yellow
            "Office Furniture": "#EF4444",  # Red
            "Software Development": "#EC4899",  # Pink
            "IT Services": "#8B5CF6",  # Purple
            "Cloud Infrastructure": "#14B8A6",  # Teal
            "Telecom": "#06B6D4",  # Cyan
            "Software Services": "#84CC16",  # Light Green
            "Software Licenses": "#F97316",  # Orange
            "Fuel & Transport": "#FB923C",  # Light Orange
            "IT Consulting": "#DC2626",  # Dark Red
            "Cloud Services": "#1E40AF",  # Dark Blue
        }

        for bill in all_bills:
            category = bill.category or "Other"
            amount = bill.amount
            category_totals[category] += amount

        # Calculate total for percentage
        total_spending = sum(category_totals.values())

        result = []
        for category, amount in sorted(
            category_totals.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                float((amount / total_spending * 100)) if total_spending > 0 else 0.0
            )
            result.append(
                {
                    "category": category,
                    "amount": float(amount),
                    "amount_display": self._in_lakhs(amount),
                    "percentage": round(percentage, 1),
                    "color": category_colors.get(category, "#6B7280"),  # Default gray
                }
            )

        return result

    def _calculate_monthly_trend(self, all_bills, paid_payments):
        """Calculate monthly trend for billed vs paid"""
        today = timezone.now().date()
        trend_data = []

        # Get last 6 months
        for i in range(5, -1, -1):  # Last 6 months
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)

            # Calculate month end
            if month_start.month == 12:
                month_end = month_start.replace(
                    year=month_start.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                month_end = month_start.replace(
                    month=month_start.month + 1, day=1
                ) - timedelta(days=1)

            # Calculate billed amount (bills created in this month)
            billed = Decimal("0")
            for bill in all_bills:
                if month_start <= bill.bill_date <= month_end:
                    billed += bill.amount

            # Calculate paid amount (payments made in this month)
            paid = Decimal("0")
            for payment in paid_payments:
                if month_start <= payment.payment_date <= month_end:
                    paid += payment.amount

            month_display = month_start.strftime("%b %Y")
            month_short = month_start.strftime("%b")

            trend_data.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "month_display": month_display,
                    "billed": float(billed),
                    "billed_display": self._in_lakhs(billed),
                    "paid": float(paid),
                    "paid_display": self._in_lakhs(paid),
                }
            )

        return trend_data

    def _calculate_top_vendors(self, all_bills):
        """Calculate top 5 vendors by spending"""
        vendor_totals = defaultdict(Decimal)

        for bill in all_bills:
            vendor_name = bill.get_vendor_name()
            amount = bill.amount
            vendor_totals[vendor_name] += amount

        # Get top 5 vendors
        top_vendors = sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        result = []
        for vendor_name, amount in top_vendors:
            result.append(
                {
                    "vendor_name": vendor_name,
                    "amount": float(amount),
                    "amount_display": self._in_lakhs(amount),
                }
            )

        return result

    def _calculate_payment_methods(self, paid_payments):
        """Calculate payment methods distribution"""
        method_totals = defaultdict(Decimal)

        # Color mapping for payment methods
        method_colors = {
            "Bank Transfer": "#3B82F6",  # Blue
            "NEFT": "#F59E0B",  # Orange
            "RTGS": "#10B981",  # Green
            "IMPS": "#EF4444",  # Red
            "Cheque": "#3B82F6",  # Blue
            "UPI": "#EC4899",  # Pink
            "Cash": "#6B7280",  # Gray
            "Credit Card": "#8B5CF6",  # Purple
        }

        for payment in paid_payments:
            method = payment.payment_method
            amount = payment.amount
            method_totals[method] += amount

        # Calculate total for percentage
        total_payments = sum(method_totals.values())

        result = []
        for method, amount in sorted(
            method_totals.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                float((amount / total_payments * 100)) if total_payments > 0 else 0.0
            )
            result.append(
                {
                    "payment_method": method,
                    "amount": float(amount),
                    "amount_display": self._in_lakhs(amount),
                    "percentage": round(percentage, 1),
                    "color": method_colors.get(method, "#6B7280"),  # Default gray
                }
            )

        return result

    def get(self, request, *args, **kwargs):
        """Get all AP analytics data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "spending_by_category": [],
                    "monthly_trend": [],
                    "top_vendors": [],
                    "payment_methods": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get all bills
        all_bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Get all payments
        paid_payments = BillPayment.objects.filter(company=company)

        # Calculate analytics
        spending_by_category = self._calculate_spending_by_category(all_bills)
        monthly_trend = self._calculate_monthly_trend(all_bills, paid_payments)
        top_vendors = self._calculate_top_vendors(all_bills)
        payment_methods = self._calculate_payment_methods(paid_payments)

        response_data = {
            "spending_by_category": spending_by_category,
            "monthly_trend": monthly_trend,
            "top_vendors": top_vendors,
            "payment_methods": payment_methods,
        }

        serializer = APAnalyticsSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
