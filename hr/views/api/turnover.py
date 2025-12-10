from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.headcount import Headcount
from hr.enums import EmploymentStatus
from hr.serializers.turnover import TurnoverCompleteSerializer
from sales.views.api.utils import get_company_from_request


class TurnoverView(APIView):
    """
    Complete Turnover API
    Returns all turnover data including:
    - Overall KPIs and exit summary
    - Turnover breakdown by department
    - Turnover breakdown by tenure ranges
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get complete turnover data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get period from query params (default: last 365 days)
        period_days = int(request.query_params.get("period_days", 365))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)

        # Get active employees (current headcount)
        active_employees = Headcount.objects.filter(
            company=company, status=EmploymentStatus.ACTIVE
        )

        # Get employees who left in the period
        exited_employees = Headcount.objects.filter(
            company=company,
            status__in=[EmploymentStatus.RESIGNED, EmploymentStatus.INACTIVE],
            end_date__gte=start_date,
            end_date__lte=end_date,
        )

        total_exits = exited_employees.count()
        active_count = active_employees.count()

        # Calculate average headcount (simplified: current active + half of exits)
        avg_headcount = (
            active_count + (total_exits / 2) if total_exits > 0 else active_count
        )

        # Calculate turnover rate: (Terminated Employees / Average Headcount) × 100
        turnover_rate = (
            (Decimal(str(total_exits)) / Decimal(str(avg_headcount)) * Decimal("100"))
            if avg_headcount > 0
            else Decimal("0.00")
        )

        # Calculate retention rate: 100 - turnover_rate
        retention_rate = Decimal("100.00") - turnover_rate

        # Calculate average tenure for active employees
        avg_tenure = self._calculate_avg_tenure(active_employees)

        # Exit summary
        # Count resigned employees who exited in the period (to match total_exits)
        resigned_count = Headcount.objects.filter(
            company=company,
            status=EmploymentStatus.RESIGNED,
            end_date__gte=start_date,
            end_date__lte=end_date,
        ).count()

        # Count terminated/inactive employees who exited in the period
        terminated_count = exited_employees.filter(
            status=EmploymentStatus.INACTIVE
        ).count()

        # Count inactive employees without end_date (on leave)
        on_leave_count = Headcount.objects.filter(
            company=company, status=EmploymentStatus.INACTIVE, end_date__isnull=True
        ).count()

        # Build KPIs
        kpis = {
            "turnover_rate": turnover_rate.quantize(Decimal("0.1")),
            "turnover_rate_display": f"{turnover_rate.quantize(Decimal('0.1'))}%",
            "total_exits": total_exits,
            "total_exits_display": f"{total_exits} ({turnover_rate.quantize(Decimal('0.1'))}% of workforce)",
            "retention_rate": retention_rate.quantize(Decimal("0.1")),
            "retention_rate_display": f"{retention_rate.quantize(Decimal('0.1'))}%",
            "avg_tenure": avg_tenure,
            "avg_tenure_display": f"{avg_tenure} yrs",
        }

        # Build exit summary
        exit_summary = {
            "active_employees": active_count,
            "resigned": resigned_count,
            "terminated": terminated_count,
            "on_leave": on_leave_count,
        }

        # Build turnover by department
        by_department = self._get_turnover_by_department(
            company, start_date, end_date, active_count, total_exits
        )

        # Build turnover by tenure
        by_tenure = self._get_turnover_by_tenure(exited_employees, total_exits)

        # Combine all data
        data = {
            "kpis": kpis,
            "exit_summary": exit_summary,
            "by_department": by_department,
            "by_tenure": by_tenure,
        }

        serializer = TurnoverCompleteSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_turnover_by_department(
        self, company, start_date, end_date, total_active, total_exits
    ):
        """Calculate turnover breakdown by department"""
        # Get active employees by department
        active_by_dept = (
            Headcount.objects.filter(
                company=company,
                status=EmploymentStatus.ACTIVE,
                department__isnull=False,
            )
            .values("department__name", "department__id")
            .annotate(active_count=Count("id"))
        )

        # Get exits by department - manually iterate to handle cases properly
        all_exits = Headcount.objects.filter(
            company=company,
            status__in=[EmploymentStatus.RESIGNED, EmploymentStatus.INACTIVE],
            end_date__gte=start_date,
            end_date__lte=end_date,
        ).select_related("department")

        # Manually count exits by department
        exits_by_dept_dict = {}
        for exit_emp in all_exits:
            dept_name = None
            if exit_emp.department:
                dept_name = (
                    exit_emp.department.name.strip()
                    if exit_emp.department.name
                    else None
                )
            # If department is NULL, we can't assign it to a department, so skip

            if dept_name:
                exits_by_dept_dict[dept_name] = exits_by_dept_dict.get(dept_name, 0) + 1

        # Create maps - handle None department names and normalize
        active_map = {}
        for item in active_by_dept:
            dept_name = item["department__name"]
            if dept_name:  # Only include if department name exists
                dept_name = dept_name.strip()  # Normalize whitespace
                active_map[dept_name] = {
                    "count": item["active_count"],
                    "id": item["department__id"],
                }

        # Use the manually counted exits
        exits_map = exits_by_dept_dict

        # Get all unique departments (from both active and exits)
        all_dept_names = set(active_map.keys()) | set(exits_map.keys())

        breakdown = []

        for dept_name in all_dept_names:
            active_count = active_map.get(dept_name, {}).get("count", 0)
            exits = exits_map.get(dept_name, 0)

            # Total employees = active + exits (employees who were in this dept)
            total_employees = active_count + exits

            # Calculate average headcount for department
            # Average = (start_of_period + end_of_period) / 2
            # Start = total_employees (active + exits), End = active_count
            # Average = (total_employees + active_count) / 2 = active + (exits / 2)
            avg_headcount = active_count + (exits / 2) if exits > 0 else total_employees

            # Calculate turnover rate
            turnover_rate = (
                (Decimal(str(exits)) / Decimal(str(avg_headcount)) * Decimal("100"))
                if avg_headcount > 0
                else Decimal("0.00")
            )

            status_label = self._get_turnover_status(turnover_rate)

            breakdown.append(
                {
                    "department": dept_name,
                    "total_employees": total_employees,
                    "exits": exits,
                    "turnover_rate": turnover_rate.quantize(Decimal("0.1")),
                    "turnover_rate_display": f"{turnover_rate.quantize(Decimal('0.1'))}%",
                    "status": status_label,
                }
            )

        # Sort breakdown by turnover rate descending
        breakdown.sort(key=lambda x: float(x["turnover_rate"]), reverse=True)

        return breakdown

    def _get_turnover_by_tenure(self, exited_employees, total_exits):
        """Calculate turnover breakdown by tenure ranges"""
        # Define tenure ranges
        tenure_ranges = [
            {"label": "0-6 months", "min_days": 0, "max_days": 180},
            {"label": "6-12 months", "min_days": 181, "max_days": 365},
            {"label": "1-2 years", "min_days": 366, "max_days": 730},
            {"label": "2-3 years", "min_days": 731, "max_days": 1095},
            {"label": "3-5 years", "min_days": 1096, "max_days": 1825},
            {"label": "5+ years", "min_days": 1826, "max_days": None},
        ]

        breakdown = []

        for range_def in tenure_ranges:
            exits_in_range = 0

            for emp in exited_employees:
                if emp.start_date and emp.end_date:
                    tenure_days = (emp.end_date - emp.start_date).days

                    if range_def["max_days"] is None:
                        # 5+ years
                        if tenure_days >= range_def["min_days"]:
                            exits_in_range += 1
                    else:
                        if (
                            range_def["min_days"]
                            <= tenure_days
                            <= range_def["max_days"]
                        ):
                            exits_in_range += 1

            # Calculate percentage of total exits
            exit_percentage = (
                (
                    Decimal(str(exits_in_range))
                    / Decimal(str(total_exits))
                    * Decimal("100")
                )
                if total_exits > 0
                else Decimal("0.00")
            )

            # Determine status based on percentage
            status_label = self._get_tenure_status(exit_percentage)

            breakdown.append(
                {
                    "tenure_range": range_def["label"],
                    "exits": exits_in_range,
                    "exit_percentage": exit_percentage.quantize(Decimal("0.1")),
                    "status": status_label,
                }
            )

        return breakdown

    def _calculate_avg_tenure(self, queryset):
        """Calculate average tenure in years"""
        tenures = []
        today = timezone.now().date()

        for emp in queryset:
            if emp.start_date:
                end_date = emp.end_date or today
                days = (end_date - emp.start_date).days
                years = Decimal(str(days)) / Decimal("365.25")
                tenures.append(years)

        if not tenures:
            return Decimal("0.0")

        avg_tenure = sum(tenures) / Decimal(str(len(tenures)))
        return avg_tenure.quantize(Decimal("0.1"))

    def _get_turnover_status(self, turnover_rate: Decimal) -> str:
        """Get status based on turnover rate"""
        rate = float(turnover_rate)
        if rate < 5:
            return "excellent"
        elif rate < 10:
            return "good"
        elif rate < 15:
            return "average"
        elif rate < 20:
            return "warning"
        else:
            return "critical"

    def _get_tenure_status(self, exit_percentage: Decimal) -> str:
        """Get status based on exit percentage"""
        # High: >20%, Medium: 10-20%, Low: <10%
        percentage = float(exit_percentage)
        if percentage > 20:
            return "High"
        elif percentage >= 10:
            return "Medium"
        else:
            return "Low"
