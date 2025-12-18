from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
from calendar import monthrange
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.models.recurring import (
    RecurringExpense,
    RecurringExpenseFrequencyChoices,
    RecurringExpenseStatusChoices,
)
from expense.views.api.bills import get_company_from_request
from financial.enums import BillsStatusChoices


class ExpenseDashboardView(APIView):
    """
    Combined API endpoint for Expense Dashboard data.

    GET /api/expense/dashboard/
    - Returns all dashboard data in one response:
      * KPIs: Total OpEx, Avg Expense, Total GST Input, ITC Available, Total TDS, Net Payable, Total Expenses, Total Amount, Avg per Bill, Categories
      * Category Distribution: Donut chart data
      * Top 5 Expenses: Highest value bills
      * Abnormal Expenses: Outliers detected
      * Subscription Spend: Monthly/annual estimates and recurring vendors
      * Vendor Concentration: Top vendors by spend percentage
      * Monthly Trend: Last 6 months with MoM change, avg, high, low
    - Query parameters:
      * months (optional): Number of months for trends (default: 6)
      * date_filter (optional): Date filter type - 'today', 'yesterday', 'this_week', 'previous_week',
                                'this_month', 'previous_month', 'this_quarter', 'previous_quarter',
                                'this_fy', 'fy_to_date', 'previous_fy', 'all_data', 'custom'
      * start_date (optional): Start date for 'custom' filter (format: YYYY-MM-DD)
      * end_date (optional): End date for 'custom' filter (format: YYYY-MM-DD)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores with Indian numbering"""
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

    @staticmethod
    def _format_amount_indian(amount: Decimal) -> str:
        """Format amount with Indian numbering system (lakhs/crores)"""
        if amount == 0:
            return "₹0"
        if amount >= 10000000:
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"
        elif amount >= 100000:
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:
            return f"₹{amount:,.2f}"

    def _is_eligible_for_itc(self, bill):
        """Determine if bill is eligible for ITC"""
        has_gstin = (
            (bill.vendor and bill.vendor.gstin)
            or bill.vendor_gstin
            or (bill.vendor and hasattr(bill.vendor, "gstin") and bill.vendor.gstin)
        )
        has_gst = bill.cgst_amount > 0 or bill.sgst_amount > 0 or bill.igst_amount > 0
        is_marked_ineligible = (
            bill.eligibility and "not eligible" in bill.eligibility.lower()
        )
        return has_gstin and has_gst and not is_marked_ineligible

    @staticmethod
    def _get_fiscal_year_dates(date):
        """Get fiscal year start and end dates (April 1 to March 31) for a given date"""
        if date.month >= 4:
            # Current fiscal year
            fy_start = datetime(date.year, 4, 1).date()
            fy_end = datetime(date.year + 1, 3, 31).date()
        else:
            # Previous fiscal year
            fy_start = datetime(date.year - 1, 4, 1).date()
            fy_end = datetime(date.year, 3, 31).date()
        return fy_start, fy_end

    def _get_date_range(self, date_filter, start_date=None, end_date=None):
        """
        Calculate date range based on filter type.
        Returns (start_date, end_date) tuple.
        """
        today = timezone.now().date()

        if date_filter == "today":
            return today, today

        elif date_filter == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday

        elif date_filter == "this_week":
            # Monday to Sunday of current week
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            return week_start, week_end

        elif date_filter == "previous_week":
            days_since_monday = today.weekday()
            current_week_start = today - timedelta(days=days_since_monday)
            previous_week_start = current_week_start - timedelta(days=7)
            previous_week_end = previous_week_start + timedelta(days=6)
            return previous_week_start, previous_week_end

        elif date_filter == "this_month":
            month_start = today.replace(day=1)
            last_day = monthrange(today.year, today.month)[1]
            month_end = today.replace(day=last_day)
            return month_start, month_end

        elif date_filter == "previous_month":
            first_day_current_month = today.replace(day=1)
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            previous_month_start = last_day_previous_month.replace(day=1)
            return previous_month_start, last_day_previous_month

        elif date_filter == "this_quarter":
            current_month = today.month
            if current_month <= 3:
                quarter_start = datetime(today.year, 1, 1).date()
                quarter_end = datetime(today.year, 3, 31).date()
            elif current_month <= 6:
                quarter_start = datetime(today.year, 4, 1).date()
                quarter_end = datetime(today.year, 6, 30).date()
            elif current_month <= 9:
                quarter_start = datetime(today.year, 7, 1).date()
                quarter_end = datetime(today.year, 9, 30).date()
            else:
                quarter_start = datetime(today.year, 10, 1).date()
                quarter_end = datetime(today.year, 12, 31).date()
            return quarter_start, quarter_end

        elif date_filter == "previous_quarter":
            current_month = today.month
            if current_month <= 3:
                # Previous quarter is Q4 of last year
                quarter_start = datetime(today.year - 1, 10, 1).date()
                quarter_end = datetime(today.year - 1, 12, 31).date()
            elif current_month <= 6:
                quarter_start = datetime(today.year, 1, 1).date()
                quarter_end = datetime(today.year, 3, 31).date()
            elif current_month <= 9:
                quarter_start = datetime(today.year, 4, 1).date()
                quarter_end = datetime(today.year, 6, 30).date()
            else:
                quarter_start = datetime(today.year, 7, 1).date()
                quarter_end = datetime(today.year, 9, 30).date()
            return quarter_start, quarter_end

        elif date_filter == "this_fy":
            # Current fiscal year (April 1 to March 31)
            fy_start, fy_end = self._get_fiscal_year_dates(today)
            return fy_start, fy_end

        elif date_filter == "fy_to_date":
            # Fiscal year start to today
            fy_start, _ = self._get_fiscal_year_dates(today)
            return fy_start, today

        elif date_filter == "previous_fy":
            # Previous fiscal year
            if today.month >= 4:
                fy_start = datetime(today.year - 1, 4, 1).date()
                fy_end = datetime(today.year, 3, 31).date()
            else:
                fy_start = datetime(today.year - 2, 4, 1).date()
                fy_end = datetime(today.year - 1, 3, 31).date()
            return fy_start, fy_end

        elif date_filter == "custom":
            # Use provided start_date and end_date
            if start_date and end_date:
                try:
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    return start_date, end_date
                except ValueError:
                    # Invalid date format, return None to indicate no filter
                    return None, None
            return None, None

        elif date_filter == "all_data" or not date_filter:
            # No date filter - return all data
            return None, None

        # Default: no filter
        return None, None

    def get(self, request, *args, **kwargs):
        """Get all dashboard data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "kpis": {
                        "total_opex": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "mom_change": 0.0,
                        },
                        "avg_expense": {"amount": 0, "amount_display": "₹0"},
                        "total_gst_input": {"amount": 0, "amount_display": "₹0"},
                        "itc_available": {"amount": 0, "amount_display": "₹0"},
                        "total_tds": {"amount": 0, "amount_display": "₹0"},
                        "net_payable": {"amount": 0, "amount_display": "₹0"},
                        "total_expenses": 0,
                        "total_amount": {"amount": 0, "amount_display": "₹0"},
                        "avg_per_bill": {"amount": 0, "amount_display": "₹0"},
                        "categories_count": 0,
                    },
                    "category_distribution": [],
                    "top_5_expenses": [],
                    "abnormal_expenses": [],
                    "subscription_spend": {
                        "monthly": {"amount": 0, "amount_display": "₹0"},
                        "annual_estimate": {"amount": 0, "amount_display": "₹0"},
                        "recurring_vendors": [],
                        "due_soon_count": 0,
                    },
                    "vendor_concentration": {
                        "top_vendors": [],
                        "is_diversified": True,
                    },
                    "monthly_trend": {
                        "data": [],
                        "mom_change": 0.0,
                        "avg_per_month": {"amount": 0, "amount_display": "₹0"},
                        "high": {"amount": 0, "amount_display": "₹0"},
                        "low": {"amount": 0, "amount_display": "₹0"},
                    },
                },
                status=status.HTTP_200_OK,
            )

        # Get query parameters
        months = int(request.query_params.get("months", 6))
        date_filter = request.query_params.get("date_filter", "all_data")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Get all bills (excluding cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Apply date filter if specified
        filter_start_date, filter_end_date = self._get_date_range(
            date_filter, start_date, end_date
        )
        if filter_start_date is not None and filter_end_date is not None:
            bills = bills.filter(
                bill_date__gte=filter_start_date, bill_date__lte=filter_end_date
            )

        # Calculate KPIs
        total_opex = sum(bill.total for bill in bills)
        total_expenses_count = bills.count()
        avg_expense = (
            total_opex / Decimal(total_expenses_count)
            if total_expenses_count > 0
            else Decimal("0")
        )

        # Calculate GST and TDS
        total_gst_input = sum(
            bill.cgst_amount + bill.sgst_amount + bill.igst_amount for bill in bills
        )
        total_tds = sum(bill.tds_amount for bill in bills)
        net_payable = total_opex - total_tds

        # Calculate ITC Available
        itc_available = Decimal("0")
        for bill in bills:
            if self._is_eligible_for_itc(bill):
                itc_available += bill.cgst_amount + bill.sgst_amount + bill.igst_amount

        # Get unique categories
        categories = (
            bills.exclude(category="")
            .exclude(category__isnull=True)
            .values_list("category", flat=True)
            .distinct()
        )
        categories_count = len(categories)

        # Calculate MoM Change
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=32)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)

        current_month_bills = bills.filter(
            bill_date__year=current_month_start.year,
            bill_date__month=current_month_start.month,
        )
        last_month_bills = bills.filter(
            bill_date__year=last_month_start.year,
            bill_date__month=last_month_start.month,
        )

        current_month_total = sum(bill.total for bill in current_month_bills)
        last_month_total = sum(bill.total for bill in last_month_bills)
        mom_change = (
            float(((current_month_total - last_month_total) / last_month_total) * 100)
            if last_month_total > 0
            else 0.0
        )

        # Category Distribution
        category_data = defaultdict(lambda: Decimal("0"))
        for bill in bills:
            category = bill.category or "Uncategorized"
            category_data[category] += bill.total

        total_for_distribution = sum(category_data.values())
        category_distribution = []
        category_colors = {
            "Personnel Expenses": "#000000",
            "Technology & Infrastructure": "#10B981",
            "Marketing & Sales": "#EC4899",
            "Establishment Expenses": "#6B7280",
            "Professional & Legal": "#4B5563",
            "Financial Expenses": "#3B82F6",
            "Travel & Conveyance": "#F97316",
            "Depreciation & Amortization": "#9CA3AF",
            "Miscellaneous Expenses": "#F97316",
            "Statutory & Taxes": "#8B5CF6",
            "Administrative Expenses": "#991B1B",
        }

        for category, amount in sorted(
            category_data.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                float((amount / total_for_distribution) * 100)
                if total_for_distribution > 0
                else 0.0
            )
            category_distribution.append(
                {
                    "category": category,
                    "amount": float(amount),
                    "amount_display": self._format_amount(amount),
                    "percentage": round(percentage, 1),
                    "color": category_colors.get(category, "#6B7280"),
                }
            )

        # Top 5 Expenses
        top_5_expenses = []
        top_bills = bills.order_by("-total")[:5]
        for bill in top_bills:
            top_5_expenses.append(
                {
                    "id": str(bill.id),
                    "name": bill.item_name or bill.get_vendor_name() or "Unknown",
                    "bill_number": bill.bill_number,
                    "amount": float(bill.total),
                    "amount_display": self._format_amount(bill.total),
                    "vendor_name": bill.get_vendor_name(),
                }
            )

        # Abnormal Expenses (Outliers)
        # Calculate average per category
        category_averages = {}
        category_counts = defaultdict(int)
        for bill in bills:
            category = bill.category or "Uncategorized"
            category_averages[category] = (
                category_averages.get(category, Decimal("0")) + bill.total
            )
            category_counts[category] += 1

        for category in category_averages:
            if category_counts[category] > 0:
                category_averages[category] = category_averages[category] / Decimal(
                    category_counts[category]
                )

        abnormal_expenses = []
        for bill in bills:
            category = bill.category or "Uncategorized"
            category_avg = category_averages.get(category, Decimal("0"))
            if category_avg > 0 and bill.total > category_avg * Decimal(
                "1.5"
            ):  # 50% above average
                percentage_above = float(
                    ((bill.total - category_avg) / category_avg) * 100
                )
                abnormal_expenses.append(
                    {
                        "id": str(bill.id),
                        "bill_number": bill.bill_number,
                        "name": bill.item_name or bill.get_vendor_name() or "Unknown",
                        "amount": float(bill.total),
                        "amount_display": self._format_amount(bill.total),
                        "category": category,
                        "percentage_above_avg": round(percentage_above, 1),
                    }
                )

        # Sort by percentage above average (descending) and limit to top outliers
        abnormal_expenses.sort(key=lambda x: x["percentage_above_avg"], reverse=True)
        abnormal_expenses = abnormal_expenses[:10]  # Top 10 outliers

        # Subscription Spend (from Recurring Expenses)
        recurring_expenses = RecurringExpense.objects.filter(
            company=company, status=RecurringExpenseStatusChoices.ACTIVE
        )

        monthly_subscription_spend = Decimal("0")
        recurring_vendors_data = defaultdict(lambda: Decimal("0"))

        for expense in recurring_expenses:
            total_amount = expense.get_total_amount()
            vendor_name = expense.get_vendor_display()

            if expense.frequency == RecurringExpenseFrequencyChoices.MONTHLY:
                monthly_subscription_spend += total_amount
                recurring_vendors_data[vendor_name] += total_amount
            elif expense.frequency == RecurringExpenseFrequencyChoices.QUARTERLY:
                monthly_amount = total_amount / Decimal("3")
                monthly_subscription_spend += monthly_amount
                recurring_vendors_data[vendor_name] += monthly_amount
            elif expense.frequency == RecurringExpenseFrequencyChoices.SEMI_ANNUAL:
                monthly_amount = total_amount / Decimal("6")
                monthly_subscription_spend += monthly_amount
                recurring_vendors_data[vendor_name] += monthly_amount
            elif expense.frequency == RecurringExpenseFrequencyChoices.ANNUAL:
                monthly_amount = total_amount / Decimal("12")
                monthly_subscription_spend += monthly_amount
                recurring_vendors_data[vendor_name] += monthly_amount

        annual_estimate = monthly_subscription_spend * Decimal("12")

        # Recurring vendors breakdown
        recurring_vendors = []
        total_recurring = sum(recurring_vendors_data.values())
        for vendor_name, amount in sorted(
            recurring_vendors_data.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            percentage = (
                float((amount / total_recurring) * 100) if total_recurring > 0 else 0.0
            )
            recurring_vendors.append(
                {
                    "vendor_name": vendor_name,
                    "amount": float(amount),
                    "amount_display": self._format_amount(amount),
                    "percentage": round(percentage, 1),
                }
            )

        # Due soon count (within 7 days)
        due_soon_count = sum(
            1 for expense in recurring_expenses if expense.is_due_soon(days=7)
        )

        # Vendor Concentration
        vendor_data = defaultdict(lambda: {"amount": Decimal("0"), "name": "Unknown"})
        for bill in bills:
            vendor_name = bill.get_vendor_name() or "Unknown"
            vendor_key = str(bill.vendor_id) if bill.vendor_id else vendor_name
            vendor_data[vendor_key]["amount"] += bill.total
            vendor_data[vendor_key]["name"] = vendor_name

        top_vendors = []
        total_vendor_spend = sum(data["amount"] for data in vendor_data.values())
        for vendor_key, data in sorted(
            vendor_data.items(), key=lambda x: x[1]["amount"], reverse=True
        )[:5]:
            percentage = (
                float((data["amount"] / total_vendor_spend) * 100)
                if total_vendor_spend > 0
                else 0.0
            )
            top_vendors.append(
                {
                    "vendor_name": data["name"],
                    "amount": float(data["amount"]),
                    "amount_display": self._format_amount(data["amount"]),
                    "percentage": round(percentage, 1),
                }
            )

        # Check if diversified (top vendor < 50% of total)
        is_diversified = True
        if top_vendors and total_vendor_spend > 0:
            top_vendor_percentage = top_vendors[0]["percentage"]
            is_diversified = top_vendor_percentage < 50.0

        # Monthly Trend (Last 6 months)
        monthly_trend_data = []
        monthly_amounts = []

        for i in range(months - 1, -1, -1):
            month_date = (current_month_start - timedelta(days=30 * i)).replace(day=1)
            last_day = monthrange(month_date.year, month_date.month)[1]
            month_end = month_date.replace(day=last_day)

            month_bills = bills.filter(
                bill_date__year=month_date.year, bill_date__month=month_date.month
            )
            month_total = sum(bill.total for bill in month_bills)
            monthly_amounts.append(month_total)

            monthly_trend_data.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "month_display": month_date.strftime("%b %Y"),
                    "amount": float(month_total),
                    "amount_display": self._format_amount(month_total),
                }
            )

        # Calculate MoM change for trend (current vs previous)
        trend_mom_change = 0.0
        if len(monthly_amounts) >= 2:
            current = monthly_amounts[-1]
            previous = monthly_amounts[-2]
            if previous > 0:
                trend_mom_change = float(((current - previous) / previous) * 100)

        avg_per_month = (
            sum(monthly_amounts) / Decimal(len(monthly_amounts))
            if monthly_amounts
            else Decimal("0")
        )
        high_amount = max(monthly_amounts) if monthly_amounts else Decimal("0")
        low_amount = min(monthly_amounts) if monthly_amounts else Decimal("0")

        # Build response
        kpis = {
            "total_opex": {
                "amount": float(total_opex),
                "amount_display": self._format_amount_indian(total_opex),
                "mom_change": round(mom_change, 1),
            },
            "avg_expense": {
                "amount": float(avg_expense),
                "amount_display": self._format_amount(avg_expense),
            },
            "total_gst_input": {
                "amount": float(total_gst_input),
                "amount_display": self._format_amount_indian(total_gst_input),
            },
            "itc_available": {
                "amount": float(itc_available),
                "amount_display": self._format_amount_indian(itc_available),
            },
            "total_tds": {
                "amount": float(total_tds),
                "amount_display": self._format_amount_indian(total_tds),
            },
            "net_payable": {
                "amount": float(net_payable),
                "amount_display": self._format_amount_indian(net_payable),
            },
            "total_expenses": total_expenses_count,
            "total_amount": {
                "amount": float(total_opex),
                "amount_display": self._format_amount_indian(total_opex),
            },
            "avg_per_bill": {
                "amount": float(avg_expense),
                "amount_display": self._format_amount(avg_expense),
            },
            "categories_count": categories_count,
        }

        subscription_spend = {
            "monthly": {
                "amount": float(monthly_subscription_spend),
                "amount_display": self._format_amount_indian(
                    monthly_subscription_spend
                ),
            },
            "annual_estimate": {
                "amount": float(annual_estimate),
                "amount_display": self._format_amount_indian(annual_estimate),
            },
            "recurring_vendors": recurring_vendors,
            "due_soon_count": due_soon_count,
        }

        vendor_concentration = {
            "top_vendors": top_vendors,
            "is_diversified": is_diversified,
        }

        monthly_trend = {
            "data": monthly_trend_data,
            "mom_change": round(trend_mom_change, 1),
            "avg_per_month": {
                "amount": float(avg_per_month),
                "amount_display": self._format_amount_indian(avg_per_month),
            },
            "high": {
                "amount": float(high_amount),
                "amount_display": self._format_amount_indian(high_amount),
            },
            "low": {
                "amount": float(low_amount),
                "amount_display": self._format_amount_indian(low_amount),
            },
        }

        return Response(
            {
                "kpis": kpis,
                "category_distribution": category_distribution,
                "top_5_expenses": top_5_expenses,
                "abnormal_expenses": abnormal_expenses,
                "subscription_spend": subscription_spend,
                "vendor_concentration": vendor_concentration,
                "monthly_trend": monthly_trend,
            },
            status=status.HTTP_200_OK,
        )
