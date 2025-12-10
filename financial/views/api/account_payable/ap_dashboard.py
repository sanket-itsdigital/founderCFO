from decimal import Decimal
from datetime import timedelta
from collections import defaultdict

from django.db.models import F, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.utils import get_user_company
from financial.models.account_payable.bills import Bill
from financial.models.account_payable.payment import BillPayment
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.ap_dashboard import APDashboardSerializer


class APDashboardView(APIView):
    """
    Comprehensive AP Dashboard API that returns all key metrics:
    - Key Performance Indicators (KPIs)
    - AP Health Status
    - Ageing Distribution
    - Key Insights
    - Ageing Breakdown
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
    def _in_thousands(amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return APDashboardView._in_lakhs(amount)
        else:
            return APDashboardView._in_thousands(amount)

    def _calculate_dpo(self, total_payables, total_billed_last_90_days):
        """Calculate Days Payable Outstanding (DPO)"""
        if total_billed_last_90_days == 0:
            return 0
        # DPO = (Total Payables / Total Billed) * Number of Days
        # Using 90 days as the period
        dpo = (total_payables / total_billed_last_90_days) * 90
        return int(dpo)

    def _calculate_payment_efficiency(self, on_time_payments, total_payments):
        """Calculate Payment Efficiency percentage"""
        if total_payments == 0:
            return 0.0  # If no payments, return 0% (no data available)
        efficiency = (on_time_payments / total_payments) * 100
        return round(float(efficiency), 1)

    def _calculate_avg_payment_days(self, paid_bills):
        """Calculate average payment days"""
        if not paid_bills:
            return 0

        total_days = 0
        count = 0
        for bill in paid_bills:
            # Get the first payment date for this bill
            first_payment = bill.payments.order_by("payment_date").first()
            if first_payment:
                payment_days = (first_payment.payment_date - bill.bill_date).days
                total_days += max(0, payment_days)
                count += 1

        return int(total_days / count) if count > 0 else 0

    def _get_ap_health_status(self, overdue_percentage, dpo, dpo_target):
        """Determine overall AP health status"""
        if overdue_percentage >= 50 or dpo > dpo_target * 2:
            return "Critical"
        elif overdue_percentage >= 30 or dpo > dpo_target * 1.5:
            return "Needs Attention"
        else:
            return "Healthy"

    def _calculate_ageing_buckets(self, bills, today):
        """Calculate ageing buckets based on due date"""
        buckets = {
            "current": Decimal("0"),
            "1_30_days": Decimal("0"),
            "31_60_days": Decimal("0"),
            "61_90_days": Decimal("0"),
            "90_plus_days": Decimal("0"),
        }

        for bill in bills:
            balance = bill.balance_amount
            if balance <= 0:
                continue

            days_until_due = (bill.due_date - today).days

            # Current: Due today or overdue (0 or negative days)
            if days_until_due <= 0:
                buckets["current"] += balance
            # 1-30 Days: Due in 1-30 days
            elif days_until_due <= 30:
                buckets["1_30_days"] += balance
            # 31-60 Days: Due in 31-60 days
            elif days_until_due <= 60:
                buckets["31_60_days"] += balance
            # 61-90 Days: Due in 61-90 days
            elif days_until_due <= 90:
                buckets["61_90_days"] += balance
            # 90+ Days: Due in more than 90 days
            else:
                buckets["90_plus_days"] += balance

        return buckets

    def get(self, request, *args, **kwargs):
        """Calculate and return comprehensive AP dashboard data"""
        # Use get_user_company to get company from logged-in user only (ignore query params)
        company = get_user_company(request.user)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        today = timezone.now().date()
        last_90_days_start = today - timedelta(days=90)

        # Get all bills (excluding cancelled)
        all_bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Get outstanding bills
        outstanding_bills = all_bills.filter(amount__gt=F("paid_amount")).exclude(
            status=BillsStatusChoices.PAID
        )

        # Calculate Total Payables
        total_payables = sum(bill.balance_amount for bill in outstanding_bills)

        # Calculate Overdue
        overdue_bills = [bill for bill in outstanding_bills if bill.is_overdue]
        overdue_amount = sum(bill.balance_amount for bill in overdue_bills)
        overdue_percentage = (
            (overdue_amount / total_payables * 100) if total_payables > 0 else 0.0
        )

        # Calculate DPO
        total_billed_last_90_days = all_bills.filter(
            bill_date__gte=last_90_days_start
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        dpo = self._calculate_dpo(total_payables, total_billed_last_90_days)
        dpo_target = 30  # Standard target

        # Calculate Payment Efficiency
        paid_bills = all_bills.filter(status=BillsStatusChoices.PAID)
        on_time_payments = 0
        total_payments_count = 0

        for bill in paid_bills:
            first_payment = bill.payments.order_by("payment_date").first()
            if first_payment:
                total_payments_count += 1
                payment_days = (first_payment.payment_date - bill.bill_date).days
                due_days = (bill.due_date - bill.bill_date).days
                if payment_days <= due_days:
                    on_time_payments += 1

        payment_efficiency = self._calculate_payment_efficiency(
            on_time_payments, total_payments_count
        )

        # Calculate Discounts Captured
        all_payments = BillPayment.objects.filter(company=company)
        discounts_captured = sum(payment.discount_taken for payment in all_payments)

        # Calculate Ageing Distribution (Current vs Overdue)
        current_amount = total_payables - overdue_amount

        # Calculate Ageing Breakdown
        ageing_buckets = self._calculate_ageing_buckets(outstanding_bills, today)

        # Get AP Health Status
        ap_health_status = self._get_ap_health_status(
            overdue_percentage, dpo, dpo_target
        )
        status_message = f"{payment_efficiency}% on-time payments"

        # Generate Key Insights
        key_insights = []
        if len(overdue_bills) > 0:
            key_insights.append(
                {
                    "text": f"{len(overdue_bills)} overdue bills",
                    "type": "danger",
                    "color": "#EF4444",
                }
            )
        if dpo > dpo_target * 1.5:
            key_insights.append(
                {
                    "text": f"High DPO ({dpo} days)",
                    "type": "warning",
                    "color": "#6B7280",
                }
            )
        if discounts_captured > 0:
            key_insights.append(
                {
                    "text": f"{self._format_amount_display(discounts_captured)} saved",
                    "type": "success",
                    "color": "#3B82F6",
                }
            )
        if payment_efficiency >= 90:
            key_insights.append(
                {
                    "text": "Excellent payment record",
                    "type": "success",
                    "color": "#10B981",
                }
            )

        # Calculate average payment time percentage (placeholder - can be improved)
        avg_payment_days = self._calculate_avg_payment_days(paid_bills)
        avg_payment_time_percentage = 0.0  # Placeholder

        response_data = {
            "kpis": {
                "total_payables": float(total_payables),
                "total_payables_display": self._in_lakhs(total_payables),
                "outstanding_balance_percentage": round(overdue_percentage, 1),
                "dpo": dpo,
                "avg_payment_time_percentage": avg_payment_time_percentage,
                "payment_efficiency": payment_efficiency,
                "on_time_payment_rate": payment_efficiency,
                "overdue_amount": float(overdue_amount),
                "overdue_amount_display": self._in_lakhs(overdue_amount),
                "overdue_bills_count": len(overdue_bills),
                "overdue_percentage": round(overdue_percentage, 1),
                "discounts_captured": float(discounts_captured),
                "discounts_captured_display": self._format_amount_display(
                    discounts_captured
                ),
                "early_payment_savings_percentage": 0.0,  # Placeholder
                "total_bills": all_bills.count(),
                "all_vendor_bills_percentage": 0.0,  # Placeholder
            },
            "ap_health_status": {
                "status": ap_health_status,
                "on_time_payment_rate": payment_efficiency,
                "status_message": status_message,
            },
            "ageing_distribution": {
                "current": float(current_amount),
                "current_display": self._in_lakhs(current_amount),
                "overdue": float(overdue_amount),
                "overdue_display": self._in_lakhs(overdue_amount),
            },
            "key_insights": key_insights,
            "ageing_breakdown": {
                "current": float(ageing_buckets["current"]),
                "current_display": self._in_lakhs(ageing_buckets["current"]),
                "days_1_30": float(ageing_buckets["1_30_days"]),
                "days_1_30_display": self._in_lakhs(ageing_buckets["1_30_days"]),
                "days_31_60": float(ageing_buckets["31_60_days"]),
                "days_31_60_display": self._in_lakhs(ageing_buckets["31_60_days"]),
                "days_61_90": float(ageing_buckets["61_90_days"]),
                "days_61_90_display": self._in_lakhs(ageing_buckets["61_90_days"]),
                "days_90_plus": float(ageing_buckets["90_plus_days"]),
                "days_90_plus_display": self._in_lakhs(ageing_buckets["90_plus_days"]),
            },
        }

        serializer = APDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
