from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.views.api.bills import get_company_from_request
from financial.enums import BillsStatusChoices


class AnalyticsOverviewView(APIView):
    """
    Combined API endpoint for Analytics Overview data.

    GET /api/expense/analytics/overview/
    - Returns:
      * KPI Cards: MoM Change, Paid Rate, Pending, Categories
      * Monthly Expense Trend (time-series data)
      * Category Breakdown by Month (stacked bar chart data)
      * Expense Efficiency Insights
    - Query parameters:
      * months (optional): Number of months to include in trends (default: 12)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores"""
        if amount == 0:
            return "₹0"
        if amount < 1000:
            return f"₹{amount:,.2f}"
        elif amount < 100000:
            return f"₹{amount / 1000:.2f}K"
        elif amount < 10000000:  # Less than 1 crore
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:  # 1 crore or more
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    def get(self, request, *args, **kwargs):
        """Get all analytics overview data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "kpis": {
                        "mom_change": {
                            "percentage": 0.0,
                            "trend": "neutral",
                        },
                        "paid_rate": {
                            "percentage": 0.0,
                            "count": 0,
                        },
                        "pending": {
                            "count": 0,
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "categories": {
                            "count": 0,
                        },
                    },
                    "monthly_expense_trend": [],
                    "category_breakdown_by_month": [],
                    "expense_efficiency_insights": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get query parameters
        months = int(request.query_params.get("months", 12))

        # Get all bills (excluding cancelled)
        bills = Bill.objects.filter(company=company).exclude(
            status=BillsStatusChoices.CANCELLED
        )

        # Calculate KPIs
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)

        # Current month expenses
        current_month_bills = bills.filter(
            bill_date__year=current_month_start.year,
            bill_date__month=current_month_start.month,
        )
        current_month_total = sum(bill.total for bill in current_month_bills)

        # Last month expenses
        last_month_bills = bills.filter(
            bill_date__year=last_month_start.year,
            bill_date__month=last_month_start.month,
        )
        last_month_total = sum(bill.total for bill in last_month_bills)

        # Calculate MoM Change
        if last_month_total > 0:
            mom_change = (
                (current_month_total - last_month_total) / last_month_total
            ) * 100
        else:
            mom_change = 100.0 if current_month_total > 0 else 0.0

        # Paid Rate
        paid_bills = bills.filter(status=BillsStatusChoices.PAID)
        total_bills = bills.count()
        paid_rate = (paid_bills.count() / total_bills * 100) if total_bills > 0 else 0.0

        # Pending
        pending_bills = bills.filter(
            Q(status=BillsStatusChoices.PENDING)
            | Q(status=BillsStatusChoices.OVERDUE)
            | Q(status=BillsStatusChoices.PARTIAL)
        )
        pending_total = sum(bill.balance_amount for bill in pending_bills)

        # Categories count
        categories = (
            bills.exclude(category="").values_list("category", flat=True).distinct()
        )
        categories_count = categories.count()

        kpis = {
            "mom_change": {
                "percentage": round(mom_change, 1),
                "trend": (
                    "down" if mom_change < 0 else "up" if mom_change > 0 else "neutral"
                ),
            },
            "paid_rate": {
                "percentage": round(paid_rate, 1),
                "count": paid_bills.count(),
            },
            "pending": {
                "count": pending_bills.count(),
                "amount": float(pending_total),
                "amount_display": self._format_amount(pending_total),
            },
            "categories": {
                "count": categories_count,
            },
        }

        # Monthly Expense Trend
        monthly_trend = []
        for i in range(months - 1, -1, -1):
            month_date = (current_month_start - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_date + timedelta(days=32)).replace(day=1) - timedelta(
                days=1
            )

            month_bills = bills.filter(
                bill_date__year=month_date.year, bill_date__month=month_date.month
            )
            month_total = sum(bill.total for bill in month_bills)

            monthly_trend.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "month_display": month_date.strftime("%b %Y"),
                    "total_expenses": float(month_total),
                    "total_expenses_display": self._format_amount(month_total),
                }
            )

        # Category Breakdown by Month
        category_breakdown_by_month = []
        category_colors = {
            "Technology & Infrastructure": "#10B981",  # green
            "Travel & Conveyance": "#6B7280",  # dark grey
            "Establishment Expenses": "#92400E",  # brownish-grey
            "Marketing & Sales": "#EC4899",  # pink
            "Personnel Expenses": "#000000",  # black
            "Financial Expenses": "#3B82F6",  # light blue
            "Depreciation & Amortization": "#9CA3AF",  # lighter grey
            "Miscellaneous Expenses": "#F97316",  # orange
            "Statutory & Taxes": "#8B5CF6",  # purple
            "Professional & Legal": "#4B5563",  # darker grey
            "Administrative Expenses": "#991B1B",  # dark red
        }

        for i in range(months - 1, -1, -1):
            month_date = (current_month_start - timedelta(days=30 * i)).replace(day=1)

            month_bills = bills.filter(
                bill_date__year=month_date.year, bill_date__month=month_date.month
            )

            # Group by category for this month
            category_data = defaultdict(lambda: Decimal("0"))
            for bill in month_bills:
                category = bill.category or "Uncategorized"
                category_data[category] += bill.total

            categories_list = []
            for category, amount in sorted(
                category_data.items(), key=lambda x: x[1], reverse=True
            ):
                categories_list.append(
                    {
                        "category": category,
                        "amount": float(amount),
                        "amount_display": self._format_amount(amount),
                        "color": category_colors.get(category, "#6B7280"),
                    }
                )

            category_breakdown_by_month.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "month_display": month_date.strftime("%b %Y"),
                    "categories": categories_list,
                    "total": float(sum(category_data.values())),
                    "total_display": self._format_amount(sum(category_data.values())),
                }
            )

        # Expense Efficiency Insights
        # Calculate total spend across all time
        total_spend_all_time = sum(bill.total for bill in bills)

        # Group by category
        category_totals = defaultdict(lambda: Decimal("0"))
        for bill in bills:
            category = bill.category or "Uncategorized"
            category_totals[category] += bill.total

        # Calculate efficiency insights
        # For now, we'll use a simple logic: categories with >20% are "High", 10-20% are "Medium", <10% are "Low"
        # This can be customized based on business logic
        efficiency_insights = []
        for category, amount in sorted(
            category_totals.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                float((amount / total_spend_all_time) * 100)
                if total_spend_all_time > 0
                else 0.0
            )

            # Determine efficiency level (this is a simple example - can be customized)
            if percentage >= 20:
                efficiency_level = "High"
            elif percentage >= 10:
                efficiency_level = "Medium"
            else:
                efficiency_level = "Low"

            efficiency_insights.append(
                {
                    "category": category,
                    "efficiency_level": efficiency_level,
                    "percentage": round(percentage, 1),
                    "amount": float(amount),
                    "amount_display": self._format_amount(amount),
                }
            )

        return Response(
            {
                "kpis": kpis,
                "monthly_expense_trend": monthly_trend,
                "category_breakdown_by_month": category_breakdown_by_month,
                "expense_efficiency_insights": efficiency_insights,
            },
            status=status.HTTP_200_OK,
        )
