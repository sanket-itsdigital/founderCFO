from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Count, Avg, Min, Max, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.headcount import Headcount
from hr.enums import EmploymentStatus, Level
from hr.serializers.compensation_overview import CompensationOverviewSerializer
from sales.views.api.utils import get_company_from_request


class CompensationOverviewView(APIView):
    """
    Compensation Overview API
    Returns comprehensive compensation dashboard data including:
    - Overview metrics (avg salary, total payroll, total benefits, bonus pool)
    - Compensation by department (avg, median, min, max)
    - Salary by level (total salary, percentage of total)
    - Compensation summary (base salaries, benefits, bonus pool, total)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _round_decimal(value, decimal_places=2):
        """Round Decimal value to specified decimal places"""
        if value is None:
            return Decimal("0.00")
        quantize_str = "0." + "0" * decimal_places
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    @staticmethod
    def _calculate_median(values):
        """Calculate median from a list of Decimal values"""
        if not values:
            return Decimal("0.00")
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            median = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / Decimal("2")
        else:
            median = sorted_values[n // 2]
        return CompensationOverviewView._round_decimal(median)

    def get(self, request):
        """Get Compensation Overview data"""
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

        total_employees = active_headcounts.count()

        if total_employees == 0:
            # Return empty structure if no employees
            response_data = {
                "overview": {
                    "avg_salary_annual": Decimal("0.00"),
                    "median_salary_annual": Decimal("0.00"),
                    "total_payroll_annual": Decimal("0.00"),
                    "total_employees": 0,
                    "total_benefits_annual": Decimal("0.00"),
                    "benefits_percentage_of_payroll": Decimal("0.00"),
                    "bonus_pool_annual": Decimal("0.00"),
                    "bonus_percentage_of_base": Decimal("0.00"),
                },
                "compensation_by_department": [],
                "salary_by_level": [],
                "compensation_summary": {
                    "base_salaries": Decimal("0.00"),
                    "benefits": Decimal("0.00"),
                    "bonus_pool": Decimal("0.00"),
                    "total_compensation": Decimal("0.00"),
                },
            }
            serializer = CompensationOverviewSerializer(data=response_data)
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Calculate Overview Metrics
        salaries = [emp.salary_annual for emp in active_headcounts]
        total_salary_sum = sum(salaries) if salaries else Decimal("0.00")
        avg_salary = (
            self._round_decimal(total_salary_sum / Decimal(str(len(salaries))))
            if salaries
            else Decimal("0.00")
        )
        median_salary = self._calculate_median(salaries)

        total_payroll = self._round_decimal(
            active_headcounts.aggregate(total=Sum("salary_annual"))["total"]
            or Decimal("0.00")
        )

        total_benefits = self._round_decimal(
            active_headcounts.aggregate(total=Sum("benefits_annual"))["total"]
            or Decimal("0.00")
        )

        # Calculate bonus pool: sum of (salary * bonus_percent / 100)
        bonus_pool = Decimal("0.00")
        for emp in active_headcounts:
            if emp.bouns_percent:
                bonus_amount = emp.salary_annual * emp.bouns_percent / 100
                bonus_pool += bonus_amount
        bonus_pool = self._round_decimal(bonus_pool)

        benefits_percentage = (
            self._round_decimal(
                (total_benefits / total_payroll * 100), decimal_places=2
            )
            if total_payroll > 0
            else Decimal("0.00")
        )

        bonus_percentage = (
            self._round_decimal((bonus_pool / total_payroll * 100), decimal_places=2)
            if total_payroll > 0
            else Decimal("0.00")
        )

        overview = {
            "avg_salary_annual": avg_salary,
            "median_salary_annual": median_salary,
            "total_payroll_annual": total_payroll,
            "total_employees": total_employees,
            "total_benefits_annual": total_benefits,
            "benefits_percentage_of_payroll": benefits_percentage,
            "bonus_pool_annual": bonus_pool,
            "bonus_percentage_of_base": bonus_percentage,
        }

        # Compensation by Department
        department_data = (
            active_headcounts.filter(department__isnull=False)
            .values("department__name")
            .annotate(employee_count=Count("id"))
            .order_by("-employee_count")
        )

        compensation_by_department = []
        for dept in department_data:
            dept_name = dept["department__name"]
            dept_employees = active_headcounts.filter(department__name=dept_name)

            dept_salaries = [emp.salary_annual for emp in dept_employees]
            dept_total_sum = sum(dept_salaries) if dept_salaries else Decimal("0.00")
            dept_avg = (
                self._round_decimal(dept_total_sum / Decimal(str(len(dept_salaries))))
                if dept_salaries
                else Decimal("0.00")
            )
            dept_median = self._calculate_median(dept_salaries)
            dept_min = (
                self._round_decimal(min(dept_salaries))
                if dept_salaries
                else Decimal("0.00")
            )
            dept_max = (
                self._round_decimal(max(dept_salaries))
                if dept_salaries
                else Decimal("0.00")
            )

            compensation_by_department.append(
                {
                    "department_name": dept_name,
                    "employees": dept_employees.count(),
                    "avg_salary": dept_avg,
                    "median": dept_median,
                    "min": dept_min,
                    "max": dept_max,
                }
            )

        # Sort by avg_salary descending
        compensation_by_department.sort(key=lambda x: x["avg_salary"], reverse=True)

        # Salary by Level
        # Get all levels in order (VP, Director, Manager, Lead, Senior, Mid, Junior)
        level_order = [
            Level.VP,
            Level.DIRECTOR,
            Level.MANAGER,
            Level.LEAD,
            Level.SENIOR,
            Level.MID,
            Level.JUNIOR,
        ]

        salary_by_level = []
        for level_value in level_order:
            level_employees = active_headcounts.filter(level=level_value)
            level_count = level_employees.count()

            if level_count > 0:
                level_total_salary = self._round_decimal(
                    level_employees.aggregate(total=Sum("salary_annual"))["total"]
                    or Decimal("0.00")
                )

                level_percentage = (
                    self._round_decimal(
                        (level_total_salary / total_payroll * 100), decimal_places=2
                    )
                    if total_payroll > 0
                    else Decimal("0.00")
                )

                salary_by_level.append(
                    {
                        "level_name": level_value,
                        "employee_count": level_count,
                        "total_salary": level_total_salary,
                        "percentage_of_total": level_percentage,
                    }
                )

        # Compensation Summary
        total_compensation = self._round_decimal(
            total_payroll + total_benefits + bonus_pool
        )
        compensation_summary = {
            "base_salaries": total_payroll,
            "benefits": total_benefits,
            "bonus_pool": bonus_pool,
            "total_compensation": total_compensation,
        }

        response_data = {
            "overview": overview,
            "compensation_by_department": compensation_by_department,
            "salary_by_level": salary_by_level,
            "compensation_summary": compensation_summary,
        }

        serializer = CompensationOverviewSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
