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
from hr.models.recruitment import Recruitment, RecruitmentStatusChoices
from hr.models.budget import Budget
from hr.enums import EmploymentStatus, Level
from hr.serializers.analytics import AnalyticsSerializer
from sales.views.api.utils import get_company_from_request
from django.db.models.functions import Coalesce


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
        # Get last 6 months of hiring data to match the image
        now = timezone.now().date()
        six_months_ago = now - timedelta(days=180)

        monthly_hiring = defaultdict(int)
        hiring_records = active_headcounts.filter(
            start_date__gte=six_months_ago, start_date__lte=now
        )

        for employee in hiring_records:
            if employee.start_date:
                month_key = self._get_month_key(employee.start_date)
                monthly_hiring[month_key] += 1

        # Generate list of months with hiring data, sorted chronologically
        # Ensure we have data for the last 6 months even if count is 0
        monthly_hiring_trend = []
        current_year = now.year
        current_month = now.month

        for i in range(6):
            month = current_month - i
            year = current_year
            while month <= 0:
                month += 12
                year -= 1
            month_key = self._get_month_key(datetime(year, month, 1).date())
            monthly_hiring_trend.append(
                {"month": month_key, "hiring_count": monthly_hiring.get(month_key, 0)}
            )

        # Reverse to show oldest first
        monthly_hiring_trend.reverse()

        # 4. Recruitment Pipeline
        # Query actual Recruitment model data
        recruitment_data = (
            Recruitment.objects.filter(company=company)
            .values("status")
            .annotate(count=Count("id"))
        )

        # Create a dictionary for quick lookup
        recruitment_dict = {item["status"]: item["count"] for item in recruitment_data}

        # Build recruitment pipeline with all statuses
        # Use display names to match the image format (OPEN, IN PROGRESS, FILLED, CANCELLED)
        recruitment_pipeline = [
            {
                "status": "OPEN",
                "count": recruitment_dict.get(RecruitmentStatusChoices.OPEN, 0),
            },
            {
                "status": "IN PROGRESS",
                "count": recruitment_dict.get(RecruitmentStatusChoices.IN_PROGRESS, 0),
            },
            {
                "status": "FILLED",
                "count": recruitment_dict.get(RecruitmentStatusChoices.FILLED, 0),
            },
            {
                "status": "CANCELLED",
                "count": recruitment_dict.get(
                    "cancelled", 0
                ),  # Handle if CANCELLED exists
            },
        ]

        # 5. Average Salary by Department
        dept_salary_data = (
            active_headcounts.filter(
                department__isnull=False, salary_annual__isnull=False
            )
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
        # Query actual Budget model data for the last 6 months
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

            month_key = self._get_month_key(datetime(year, month, 1).date())

            # Get budgets for this month (where period year and month match)
            month_budgets = Budget.objects.filter(
                company=company,
                period__year=year,
                period__month=month,
            )

            # Aggregate budget and actual amounts
            budget_total = month_budgets.aggregate(
                total=Coalesce(Sum("budget_amount"), Decimal("0.00"))
            )["total"] or Decimal("0.00")
            if not isinstance(budget_total, Decimal):
                budget_total = Decimal(str(budget_total))

            actual_total = month_budgets.aggregate(
                total=Coalesce(Sum("actual_amount"), Decimal("0.00"))
            )["total"] or Decimal("0.00")
            if not isinstance(actual_total, Decimal):
                actual_total = Decimal(str(actual_total))

            budget_vs_actual.append(
                {
                    "month": month_key,
                    "budget": self._round_decimal(budget_total),
                    "actual": self._round_decimal(actual_total),
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
