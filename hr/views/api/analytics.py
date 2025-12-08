from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from calendar import monthrange
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.headcount import Headcount
from hr.enums import EmploymentStatus, Level
from hr.serializers.analytics import AnalyticsSerializer
from sales.views.api.utils import get_company_from_request


class AnalyticsView(APIView):
    """
    Analytics API
    Returns comprehensive HR analytics dashboard data including:
    - Headcount by department
    - Headcount by level (with percentages)
    - Monthly hiring trend
    - Recruitment pipeline status
    - Average salary by department
    - Budget vs actual spending
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _round_decimal(value, decimal_places=2):
        """Round Decimal value to specified decimal places"""
        if value is None:
            return Decimal("0.00")
        # Convert to Decimal if it's a float or int
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        quantize_str = "0." + "0" * decimal_places
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_month_key(date):
        """Get month key in format YYYY-MM"""
        return date.strftime("%Y-%m")

    def get(self, request):
        """Get Analytics data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get all active headcounts for the company
        active_headcounts = Headcount.objects.filter(
            company=company, status=EmploymentStatus.ACTIVE
        )

        total_headcount = active_headcounts.count()

        # 1. Headcount by Department
        department_data = (
            active_headcounts.filter(department__isnull=False)
            .values("department__name")
            .annotate(headcount=Count("id"))
            .order_by("-headcount")
        )

        headcount_by_department = [
            {
                "department_name": dept["department__name"],
                "headcount": dept["headcount"],
            }
            for dept in department_data
        ]

        # 2. Headcount by Level
        level_data = (
            active_headcounts.exclude(level__isnull=True)
            .exclude(level__exact="")
            .values("level")
            .annotate(headcount=Count("id"))
            .order_by("-headcount")
        )

        headcount_by_level = []
        for level_item in level_data:
            level_name = level_item["level"]
            level_headcount = level_item["headcount"]
            percentage = (
                self._round_decimal(
                    (
                        Decimal(str(level_headcount))
                        / Decimal(str(total_headcount))
                        * 100
                    ),
                    decimal_places=2,
                )
                if total_headcount > 0
                else Decimal("0.00")
            )

            headcount_by_level.append(
                {
                    "level_name": level_name,
                    "headcount": level_headcount,
                    "percentage": percentage,
                }
            )

        # Sort by percentage descending
        headcount_by_level.sort(key=lambda x: x["percentage"], reverse=True)

        # 3. Monthly Hiring Trend (based on start_date)
        # Get last 12 months of hiring data
        now = timezone.now().date()
        twelve_months_ago = now - timedelta(days=365)

        monthly_hiring = defaultdict(int)
        hiring_records = active_headcounts.filter(
            start_date__gte=twelve_months_ago, start_date__lte=now
        )

        for employee in hiring_records:
            month_key = self._get_month_key(employee.start_date)
            monthly_hiring[month_key] += 1

        # Generate list of months with hiring data, sorted chronologically
        monthly_hiring_trend = [
            {"month": month, "hiring_count": count}
            for month, count in sorted(monthly_hiring.items())
        ]

        # 4. Recruitment Pipeline
        # Note: This is a placeholder structure since there's no recruitment model yet
        # In a real implementation, this would query a Recruitment/JobPosting model
        # For now, returning empty or placeholder data
        recruitment_pipeline = [
            {"status": "OPEN", "count": 0},
            {"status": "IN PROGRESS", "count": 0},
            {"status": "FILLED", "count": 0},
            {"status": "CANCELLED", "count": 0},
        ]

        # 5. Average Salary by Department
        dept_salary_data = (
            active_headcounts.filter(department__isnull=False)
            .values("department__name")
            .annotate(avg_salary=Avg("salary_annual"))
            .order_by("-avg_salary")
        )

        avg_salary_by_department = [
            {
                "department_name": dept["department__name"],
                "avg_salary": self._round_decimal(
                    dept["avg_salary"] or Decimal("0.00")
                ),
            }
            for dept in dept_salary_data
        ]

        # 6. Budget vs Actual
        # Note: This is a placeholder structure since there's no budget model yet
        # In a real implementation, this would query a Budget model
        # Calculate actual monthly payroll based on employees active in each month
        # Get last 6 months
        budget_vs_actual = []
        current_year = now.year
        current_month = now.month

        for i in range(6):
            # Calculate month (go back i months)
            month = current_month - i
            year = current_year
            while month <= 0:
                month += 12
                year -= 1

            month_date = datetime(year, month, 1).date()
            month_key = self._get_month_key(month_date)

            # Calculate last day of month
            _, last_day = monthrange(year, month)
            month_end = datetime(year, month, last_day).date()

            # Get employees who were active in this month
            # Started before or during month, and (no end_date or end_date after month start)
            month_employees = Headcount.objects.filter(
                company=company,
                start_date__lte=month_end,
            ).exclude(
                # Exclude those who ended before this month
                end_date__lt=month_date
            )

            # Calculate monthly payroll (annual salary / 12)
            monthly_payroll = (
                month_employees.aggregate(total=Sum("salary_annual"))["total"]
                or Decimal("0.00")
            ) / Decimal("12")

            # Placeholder budget (5% higher than actual for demo purposes)
            # In production, this would come from a Budget model
            budget_amount = monthly_payroll * Decimal("1.05")

            budget_vs_actual.append(
                {
                    "month": month_key,
                    "budget": self._round_decimal(budget_amount),
                    "actual": self._round_decimal(monthly_payroll),
                }
            )

        # Reverse to show oldest first
        budget_vs_actual.reverse()

        response_data = {
            "headcount_by_department": headcount_by_department,
            "headcount_by_level": headcount_by_level,
            "monthly_hiring_trend": monthly_hiring_trend,
            "recruitment_pipeline": recruitment_pipeline,
            "avg_salary_by_department": avg_salary_by_department,
            "budget_vs_actual": budget_vs_actual,
        }

        serializer = AnalyticsSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
