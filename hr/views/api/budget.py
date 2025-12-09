from decimal import Decimal
from datetime import datetime, timedelta
from calendar import month_abbr

from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.budget import Budget
from hr.models.category import Category
from hr.models.headcount import Headcount
from hr.serializers.budget import BudgetDashboardSerializer
from sales.views.api.utils import get_company_from_request


class BudgetView(APIView):
    """
    Complete HR Budget Dashboard API
    Returns all budget data including:
    - KPIs (Total Budget, Actual Spend, Cost per Employee, Variance)
    - Budget vs Actual by Category
    - Budget by Department
    - Monthly Spend Trend
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_crores(amount: Decimal) -> str:
        """Convert amount to crores format (₹XX.XXCr)"""
        if amount == 0:
            return "₹0.00Cr"
        crores = amount / Decimal("10000000")
        return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as L or Cr based on value"""
        if amount >= Decimal("10000000"):
            return BudgetView._in_crores(amount)
        else:
            return BudgetView._in_lakhs(amount)

    def get(self, request):
        """Get complete budget dashboard data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get year from query params (default: current year)
        year = int(request.query_params.get("year", timezone.now().year))

        # Get all budgets for the company in the specified year
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()

        all_budgets = Budget.objects.filter(
            company=company, period__gte=start_date, period__lte=end_date
        )

        # Calculate KPIs
        kpis = self._calculate_kpis(all_budgets, company)

        # Calculate Category Breakdown
        category_breakdown = self._calculate_category_breakdown(all_budgets)

        # Calculate Department Breakdown
        department_breakdown = self._calculate_department_breakdown(all_budgets)

        # Calculate Monthly Trend
        monthly_trend = self._calculate_monthly_trend(all_budgets, year)

        data = {
            "kpis": kpis,
            "category_breakdown": category_breakdown,
            "department_breakdown": department_breakdown,
            "monthly_trend": monthly_trend,
        }

        serializer = BudgetDashboardSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _calculate_kpis(self, all_budgets, company):
        """Calculate budget KPIs"""
        # Total Budget
        total_budget = all_budgets.aggregate(
            total=Coalesce(Sum("budget_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")
        if not isinstance(total_budget, Decimal):
            total_budget = Decimal(str(total_budget))
        total_budget_display = self._format_amount_display(total_budget)

        # Actual Spend
        actual_spend = all_budgets.aggregate(
            total=Coalesce(Sum("actual_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")
        if not isinstance(actual_spend, Decimal):
            actual_spend = Decimal(str(actual_spend))
        actual_spend_display = self._format_amount_display(actual_spend)

        # Variance
        variance = actual_spend - total_budget
        variance_display = self._format_amount_display(abs(variance))
        if variance < 0:
            variance_display = f"-{variance_display}"
        else:
            variance_display = f"+{variance_display}"

        # Variance Percentage
        variance_percentage = (
            (variance / total_budget * Decimal("100"))
            if total_budget > 0
            else Decimal("0.00")
        )

        # Cost per Employee
        from hr.enums import EmploymentStatus

        active_employees = Headcount.objects.filter(
            company=company, status=EmploymentStatus.ACTIVE
        ).count()
        cost_per_employee = (
            actual_spend / Decimal(str(active_employees))
            if active_employees > 0
            else Decimal("0.00")
        )
        cost_per_employee_display = self._format_amount_display(cost_per_employee)

        return {
            "total_budget": total_budget.quantize(Decimal("0.01")),
            "total_budget_display": total_budget_display,
            "actual_spend": actual_spend.quantize(Decimal("0.01")),
            "actual_spend_display": actual_spend_display,
            "variance": variance.quantize(Decimal("0.01")),
            "variance_display": variance_display,
            "variance_percentage": variance_percentage.quantize(Decimal("0.1")),
            "cost_per_employee": cost_per_employee.quantize(Decimal("0.01")),
            "cost_per_employee_display": cost_per_employee_display,
            "active_employees": active_employees,
        }

    def _calculate_category_breakdown(self, all_budgets):
        """Calculate budget vs actual by category"""
        # Group by category
        category_data = (
            all_budgets.values("category__name")
            .annotate(
                total_budget=Coalesce(Sum("budget_amount"), Decimal("0.00")),
                total_actual=Coalesce(Sum("actual_amount"), Decimal("0.00")),
            )
            .order_by("category__name")
        )

        category_breakdown = []
        total_budget_sum = Decimal("0.00")
        total_actual_sum = Decimal("0.00")

        for item in category_data:
            category_name = item["category__name"]
            budget = (
                Decimal(str(item["total_budget"]))
                if item["total_budget"]
                else Decimal("0.00")
            )
            actual = (
                Decimal(str(item["total_actual"]))
                if item["total_actual"]
                else Decimal("0.00")
            )
            variance = actual - budget
            variance_percentage = (
                (variance / budget * Decimal("100")) if budget > 0 else Decimal("0.00")
            )

            # Determine status
            if variance_percentage < -1:
                status = "Under"
            elif variance_percentage > 1:
                status = "Over"
            else:
                status = "On Track"

            variance_display = self._format_amount_display(abs(variance))
            if variance >= 0:
                variance_display = f"+{variance_display}"
            else:
                variance_display = f"-{variance_display}"

            total_budget_sum += budget
            total_actual_sum += actual

            category_breakdown.append(
                {
                    "category": category_name,
                    "budget": budget.quantize(Decimal("0.01")),
                    "budget_display": self._format_amount_display(budget),
                    "actual": actual.quantize(Decimal("0.01")),
                    "actual_display": self._format_amount_display(actual),
                    "variance": variance.quantize(Decimal("0.01")),
                    "variance_display": variance_display,
                    "variance_percentage": variance_percentage.quantize(Decimal("0.1")),
                    "status": status,
                }
            )

        # Add total row only if there are categories
        if category_breakdown:
            total_variance = total_actual_sum - total_budget_sum
            total_variance_percentage = (
                (total_variance / total_budget_sum * Decimal("100"))
                if total_budget_sum > 0
                else Decimal("0.00")
            )

            total_variance_display = self._format_amount_display(abs(total_variance))
            if total_variance >= 0:
                total_variance_display = f"+{total_variance_display}"
            else:
                total_variance_display = f"-{total_variance_display}"

            category_breakdown.append(
                {
                    "category": "Total",
                    "budget": total_budget_sum.quantize(Decimal("0.01")),
                    "budget_display": self._format_amount_display(total_budget_sum),
                    "actual": total_actual_sum.quantize(Decimal("0.01")),
                    "actual_display": self._format_amount_display(total_actual_sum),
                    "variance": total_variance.quantize(Decimal("0.01")),
                    "variance_display": total_variance_display,
                    "variance_percentage": total_variance_percentage.quantize(
                        Decimal("0.1")
                    ),
                    "status": "-",
                }
            )

        return category_breakdown

    def _calculate_department_breakdown(self, all_budgets):
        """Calculate budget by department"""
        # Group by department
        department_data = (
            all_budgets.filter(department__isnull=False)
            .values("department__name")
            .annotate(
                total_budget=Coalesce(Sum("budget_amount"), Decimal("0.00")),
                total_actual=Coalesce(Sum("actual_amount"), Decimal("0.00")),
            )
            .order_by("department__name")
        )

        department_breakdown = []

        for item in department_data:
            department_name = item["department__name"]
            budget = (
                Decimal(str(item["total_budget"]))
                if item["total_budget"]
                else Decimal("0.00")
            )
            actual = (
                Decimal(str(item["total_actual"]))
                if item["total_actual"]
                else Decimal("0.00")
            )

            # Calculate percentage of budget used
            percentage = (
                (actual / budget * Decimal("100")) if budget > 0 else Decimal("0.00")
            )

            department_breakdown.append(
                {
                    "department": department_name,
                    "budget": budget.quantize(Decimal("0.01")),
                    "budget_display": self._format_amount_display(budget),
                    "actual": actual.quantize(Decimal("0.01")),
                    "actual_display": self._format_amount_display(actual),
                    "percentage": percentage.quantize(Decimal("0.1")),
                }
            )

        return department_breakdown

    def _calculate_monthly_trend(self, all_budgets, year):
        """Calculate monthly spend trend"""
        from django.db.models import Q

        monthly_trend = []

        for month in range(1, 13):
            # Filter budgets where period year and month match
            # Using Q objects to filter by year and month extracted from period
            month_budgets = all_budgets.filter(period__year=year, period__month=month)

            budget = month_budgets.aggregate(
                total=Coalesce(Sum("budget_amount"), Decimal("0.00"))
            )["total"] or Decimal("0.00")
            if not isinstance(budget, Decimal):
                budget = Decimal(str(budget))

            actual = month_budgets.aggregate(
                total=Coalesce(Sum("actual_amount"), Decimal("0.00"))
            )["total"] or Decimal("0.00")
            if not isinstance(actual, Decimal):
                actual = Decimal(str(actual))

            # Calculate percentage
            percentage = (
                int((actual / budget * Decimal("100")).quantize(Decimal("1")))
                if budget > 0
                else 0
            )

            monthly_trend.append(
                {
                    "month": f"{year}-{month:02d}",
                    "actual": actual.quantize(Decimal("0.01")),
                    "actual_display": self._format_amount_display(actual),
                    "budget": budget.quantize(Decimal("0.01")),
                    "budget_display": self._format_amount_display(budget),
                    "percentage": percentage,
                }
            )

        return monthly_trend
