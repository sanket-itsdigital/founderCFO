from decimal import Decimal

from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.headcount import Headcount
from hr.enums import EmploymentStatus
from hr.serializers.headcount_breakdown import (
    DepartmentBreakdownResponseSerializer,
    LocationBreakdownResponseSerializer,
    EmployeeListResponseSerializer,
)
from sales.views.api.utils import get_company_from_request


class HeadcountByDepartmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = Headcount.objects.filter(company=company, status=EmploymentStatus.ACTIVE)
        total = qs.count()
        departments_count = (
            qs.filter(department__isnull=False).values("department").distinct().count()
        )
        locations_count = (
            qs.exclude(location__isnull=True)
            .exclude(location__exact="")
            .values("location")
            .distinct()
            .count()
        )
        levels_count = (
            qs.exclude(level__isnull=True)
            .exclude(level__exact="")
            .values("level")
            .distinct()
            .count()
        )

        breakdown = []
        dept_rows = (
            qs.filter(department__isnull=False)
            .values("department__name")
            .annotate(
                headcount=Count("id"),
                avg_salary=Avg("salary_annual"),
            )
            .order_by("department__name")
        )
        for row in dept_rows:
            dept_name = row["department__name"]
            headcount = row["headcount"]
            percent = (
                (Decimal(headcount) / Decimal(total) * Decimal("100"))
                if total
                else Decimal("0")
            )
            avg_salary = row["avg_salary"] or Decimal("0")
            # tenure: approximate in years
            avg_tenure_years = self._avg_tenure_years(
                qs.filter(department__name=dept_name)
            )
            breakdown.append(
                {
                    "department": dept_name,
                    "headcount": headcount,
                    "percent_of_org": percent.quantize(Decimal("0.1")),
                    "avg_salary": avg_salary.quantize(Decimal("0.1")),
                    "avg_tenure_years": avg_tenure_years,
                    "open_positions": 0,
                }
            )

        data = {
            "total_headcount": total,
            "departments": departments_count,
            "locations": locations_count,
            "levels": levels_count,
            "breakdown": breakdown,
        }
        serializer = DepartmentBreakdownResponseSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _avg_tenure_years(self, qs):
        tenures = []
        for emp in qs:
            if emp.start_date:
                tenures.append((emp.start_date, emp.end_date))
        if not tenures:
            return Decimal("0")
        from django.utils import timezone

        today = timezone.now().date()
        total_days = 0
        for start, end in tenures:
            end_date = end or today
            total_days += (end_date - start).days
        avg_days = total_days / len(tenures)
        return (Decimal(avg_days) / Decimal("365.25")).quantize(Decimal("0.1"))


class HeadcountByLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = Headcount.objects.filter(company=company, status=EmploymentStatus.ACTIVE)
        total = qs.count()
        departments_count = (
            qs.filter(department__isnull=False).values("department").distinct().count()
        )
        locations_count = (
            qs.exclude(location__isnull=True)
            .exclude(location__exact="")
            .values("location")
            .distinct()
            .count()
        )
        levels_count = (
            qs.exclude(level__isnull=True)
            .exclude(level__exact="")
            .values("level")
            .distinct()
            .count()
        )

        breakdown = []
        loc_rows = (
            qs.exclude(location__isnull=True)
            .exclude(location__exact="")
            .values("location")
            .annotate(headcount=Count("id"), avg_salary=Avg("salary_annual"))
            .order_by("location")
        )
        for row in loc_rows:
            loc = row["location"]
            headcount = row["headcount"]
            percent = (
                (Decimal(headcount) / Decimal(total) * Decimal("100"))
                if total
                else Decimal("0")
            )
            avg_salary = row["avg_salary"] or Decimal("0")
            avg_tenure_years = self._avg_tenure_years(qs.filter(location=loc))
            depts_in_loc = (
                qs.filter(location=loc, department__isnull=False)
                .values("department")
                .distinct()
                .count()
            )
            breakdown.append(
                {
                    "location": loc,
                    "headcount": headcount,
                    "percent_of_org": percent.quantize(Decimal("0.1")),
                    "departments": depts_in_loc,
                    "avg_salary": avg_salary.quantize(Decimal("0.1")),
                    "avg_tenure_years": avg_tenure_years,
                    "open_positions": 0,
                }
            )

        data = {
            "total_headcount": total,
            "departments": departments_count,
            "locations": locations_count,
            "levels": levels_count,
            "breakdown": breakdown,
        }
        serializer = LocationBreakdownResponseSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _avg_tenure_years(self, qs):
        """Calculate average tenure in years for a queryset"""
        from django.utils import timezone

        tenures = []
        for emp in qs:
            if emp.start_date:
                tenures.append((emp.start_date, emp.end_date))
        if not tenures:
            return Decimal("0")

        today = timezone.now().date()
        total_days = 0
        for start, end in tenures:
            end_date = end or today
            total_days += (end_date - start).days
        avg_days = total_days / len(tenures)
        return (Decimal(avg_days) / Decimal("365.25")).quantize(Decimal("0.1"))


class HeadcountEmployeesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        dept = request.query_params.get("department")
        loc = request.query_params.get("location")
        qs = Headcount.objects.filter(company=company, status=EmploymentStatus.ACTIVE)
        if dept:
            qs = qs.filter(department__name=dept)
        if loc:
            qs = qs.filter(location=loc)

        results = []
        for emp in qs:
            results.append(
                {
                    "id": emp.id,
                    "name": emp.name,
                    "email": emp.email,
                    "department": emp.department.name if emp.department else None,
                    "location": emp.location,
                    "level": emp.level,
                    "salary_annual": emp.salary_annual,
                    "start_date": emp.start_date,
                    "end_date": emp.end_date,
                }
            )
        data = {"count": len(results), "results": results}
        serializer = EmployeeListResponseSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
