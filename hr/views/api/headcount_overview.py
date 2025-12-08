from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.headcount import Headcount
from hr.enums import EmploymentStatus
from hr.serializers.headcount_overview import HeadcountOverviewSerializer
from sales.views.api.utils import get_company_from_request


class HeadcountOverviewView(APIView):
    """
    Headcount Overview API
    Returns comprehensive headcount dashboard data including:
    - Overview metrics (total headcount, departments, locations)
    - Headcount by department with percentages and average tenure
    - Headcount by location with percentages
    - Level distribution with percentages
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _calculate_tenure_years(start_date):
        """Calculate tenure in years from start_date to today"""
        if not start_date:
            return None
        today = timezone.now().date()
        delta = today - start_date
        years = delta.days / 365.25
        return round(years, 1)

    def get(self, request):
        """Get Headcount Overview data"""
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

        # Overview Metrics
        # Total departments (distinct departments with active employees)
        total_departments = (
            active_headcounts.filter(department__isnull=False)
            .values("department")
            .distinct()
            .count()
        )

        # Total locations (distinct locations with active employees)
        total_locations = (
            active_headcounts.exclude(location__isnull=True)
            .exclude(location__exact="")
            .values("location")
            .distinct()
            .count()
        )

        overview = {
            "total_headcount": total_headcount,
            "total_departments": total_departments,
            "total_locations": total_locations,
        }

        # Headcount by Department
        department_data = (
            active_headcounts.filter(department__isnull=False)
            .values("department__name")
            .annotate(headcount=Count("id"))
            .order_by("-headcount")
        )

        headcount_by_department = []
        for dept in department_data:
            dept_name = dept["department__name"]
            dept_headcount = dept["headcount"]

            # Calculate percentage
            percentage = (
                round((dept_headcount / total_headcount * 100), 1)
                if total_headcount > 0
                else 0.0
            )

            # Calculate average tenure for this department
            dept_employees = active_headcounts.filter(department__name=dept_name)

            tenures = []
            for employee in dept_employees:
                tenure = self._calculate_tenure_years(employee.start_date)
                if tenure is not None:
                    tenures.append(tenure)

            avg_tenure = round(sum(tenures) / len(tenures), 1) if tenures else None

            headcount_by_department.append(
                {
                    "department_name": dept_name,
                    "headcount": dept_headcount,
                    "percentage_of_total": percentage,
                    "average_tenure_years": avg_tenure,
                }
            )

        # Add total row
        if headcount_by_department:
            headcount_by_department.append(
                {
                    "department_name": "Total",
                    "headcount": total_headcount,
                    "percentage_of_total": 100.0,
                    "average_tenure_years": None,
                }
            )

        # Headcount by Location
        location_data = (
            active_headcounts.exclude(location__isnull=True)
            .exclude(location__exact="")
            .values("location")
            .annotate(headcount=Count("id"))
            .order_by("-headcount")
        )

        headcount_by_location = []
        for loc in location_data:
            loc_name = loc["location"]
            loc_headcount = loc["headcount"]

            # Calculate percentage
            percentage = (
                round((loc_headcount / total_headcount * 100), 1)
                if total_headcount > 0
                else 0.0
            )

            headcount_by_location.append(
                {
                    "location_name": loc_name,
                    "headcount": loc_headcount,
                    "percentage": percentage,
                }
            )

        # Level Distribution
        level_data = (
            active_headcounts.exclude(level__isnull=True)
            .exclude(level__exact="")
            .values("level")
            .annotate(headcount=Count("id"))
            .order_by("-headcount")
        )

        level_distribution = []
        for level_item in level_data:
            level_name = level_item["level"]
            level_headcount = level_item["headcount"]

            # Calculate percentage
            percentage = (
                round((level_headcount / total_headcount * 100), 1)
                if total_headcount > 0
                else 0.0
            )

            level_distribution.append(
                {
                    "level_name": level_name,
                    "headcount": level_headcount,
                    "percentage": percentage,
                }
            )

        response_data = {
            "overview": overview,
            "headcount_by_department": headcount_by_department,
            "headcount_by_location": headcount_by_location,
            "level_distribution": level_distribution,
        }

        serializer = HeadcountOverviewSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
