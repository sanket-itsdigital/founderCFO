from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models.recruitment import (
    Recruitment,
    RecruitmentStatusChoices,
    RecruitmentSourceChoices,
)
from hr.serializers.recruitment import RecruitmentDashboardSerializer
from sales.views.api.utils import get_company_from_request


class RecruitmentView(APIView):
    """
    Complete Recruitment Dashboard API
    Returns all recruitment data including:
    - KPIs (Time to Hire, Cost per Hire, Offer Acceptance, Open Positions)
    - Recruitment Funnel (Applications, Interviews, Offers, Acceptances)
    - Source Effectiveness breakdown
    - Open Positions list
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get complete recruitment data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get period from query params (default: last 365 days)
        period_days = int(request.query_params.get("period_days", 365))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)

        # Get all recruitments for the company (not filtered by period for overall metrics)
        all_recruitments = Recruitment.objects.filter(company=company)

        # Get recruitments in the period (for time-based calculations like time to hire)
        period_recruitments = all_recruitments.filter(
            posting_date__gte=start_date, posting_date__lte=end_date
        )

        # Calculate KPIs (use all_recruitments for overall metrics, period_recruitments for time-based)
        kpis = self._calculate_kpis(all_recruitments, period_recruitments, company)

        # Calculate Recruitment Funnel (use all_recruitments to include all data)
        funnel = self._calculate_funnel(all_recruitments)

        # Calculate Source Effectiveness (use all_recruitments to include all sources)
        source_effectiveness = self._calculate_source_effectiveness(all_recruitments)

        # Get Open Positions
        open_positions = self._get_open_positions(company)

        data = {
            "kpis": kpis,
            "funnel": funnel,
            "source_effectiveness": source_effectiveness,
            "open_positions": open_positions,
        }

        serializer = RecruitmentDashboardSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _calculate_kpis(self, all_recruitments, period_recruitments, company):
        """Calculate recruitment KPIs"""
        # Time to Hire: Avg(Filled Date - Posted Date) for closed positions
        # Formula: Avg(actual_close_date - posting_date) for status = FILLED
        # Benchmark: Target <30 days for standard roles
        # Use period_recruitments for time-based calculation
        filled_recruitments = period_recruitments.filter(
            status=RecruitmentStatusChoices.FILLED,
            actual_close_date__isnull=False,
            posting_date__isnull=False,
        )

        time_to_hire_days = None
        if filled_recruitments.exists():
            total_days = 0
            count = 0
            for rec in filled_recruitments:
                if rec.actual_close_date and rec.posting_date:
                    days = (rec.actual_close_date - rec.posting_date).days
                    if days >= 0:  # Only count valid date differences
                        total_days += days
                        count += 1
            if count > 0:
                # Calculate average: Sum of days / Count of filled positions
                time_to_hire_days = int(round(total_days / count))

        time_to_hire_display = (
            f"{time_to_hire_days}d" if time_to_hire_days is not None else "N/A"
        )

        # Cost per Hire: Total Recruitment Cost / Number of New Hires
        # Formula: Total Recruitment Cost / Number of New Hires
        # Where:
        #   - Total Recruitment Cost = Sum of all cost_spent
        #   - Number of New Hires = Sum of all offers_accepted
        total_cost = all_recruitments.aggregate(
            total=Coalesce(Sum("cost_spent"), Decimal("0.00"))
        )["total"] or Decimal("0.00")
        if not isinstance(total_cost, Decimal):
            total_cost = Decimal(str(total_cost))

        total_hires = (
            all_recruitments.aggregate(total=Coalesce(Sum("offers_accepted"), 0))[
                "total"
            ]
            or 0
        )
        total_hires = int(total_hires) if total_hires else 0

        # Calculate cost per hire: Total Cost / Total Hires
        # Benchmark: Target <₹50,000 for mid-level positions
        cost_per_hire = (
            total_cost / Decimal(str(total_hires))
            if total_hires > 0
            else Decimal("0.00")
        )
        cost_per_hire_display = self._format_cost(cost_per_hire)

        # Add status indicator for cost per hire (optional, can be added to response)
        # cost_per_hire_status = "good" if cost_per_hire < 50000 else "warning"

        # Offer Acceptance Rate: (Offers Accepted / Offers Made) × 100
        total_offers_made = (
            all_recruitments.aggregate(total=Coalesce(Sum("offers_made"), 0))["total"]
            or 0
        )
        total_offers_made = int(total_offers_made) if total_offers_made else 0

        total_offers_accepted = (
            all_recruitments.aggregate(total=Coalesce(Sum("offers_accepted"), 0))[
                "total"
            ]
            or 0
        )
        total_offers_accepted = (
            int(total_offers_accepted) if total_offers_accepted else 0
        )

        offer_acceptance_rate = (
            (
                Decimal(str(total_offers_accepted))
                / Decimal(str(total_offers_made))
                * Decimal("100")
            )
            if total_offers_made > 0
            else Decimal("0.00")
        )
        offer_acceptance_display = f"{offer_acceptance_rate.quantize(Decimal('0.1'))}% ({total_offers_accepted} of {total_offers_made} offers)"

        # Open Positions
        open_recruitments = Recruitment.objects.filter(
            company=company,
            status__in=[
                RecruitmentStatusChoices.OPEN,
                RecruitmentStatusChoices.IN_PROGRESS,
            ],
        )
        open_positions_count = (
            open_recruitments.aggregate(total=Coalesce(Sum("positions_required"), 0))[
                "total"
            ]
            or 0
        )
        open_positions_count = int(open_positions_count) if open_positions_count else 0

        # Filled positions in period (use period_recruitments)
        filled_positions_count = (
            period_recruitments.filter(
                status=RecruitmentStatusChoices.FILLED
            ).aggregate(total=Coalesce(Sum("offers_accepted"), 0))["total"]
            or 0
        )
        filled_positions_count = (
            int(filled_positions_count) if filled_positions_count else 0
        )

        return {
            "time_to_hire": time_to_hire_days,
            "time_to_hire_display": time_to_hire_display,
            "cost_per_hire": cost_per_hire.quantize(Decimal("0.01")),
            "cost_per_hire_display": cost_per_hire_display,
            "offer_acceptance_rate": offer_acceptance_rate.quantize(Decimal("0.1")),
            "offer_acceptance_display": offer_acceptance_display,
            "open_positions": open_positions_count,
            "filled_positions": filled_positions_count,
        }

    def _calculate_funnel(self, all_recruitments):
        """Calculate recruitment funnel metrics"""
        # Calculate totals using Coalesce to handle None values
        total_applications = (
            all_recruitments.aggregate(total=Coalesce(Sum("applications_received"), 0))[
                "total"
            ]
            or 0
        )
        total_interviews = (
            all_recruitments.aggregate(total=Coalesce(Sum("interviews_conducted"), 0))[
                "total"
            ]
            or 0
        )
        total_offers_made = (
            all_recruitments.aggregate(total=Coalesce(Sum("offers_made"), 0))["total"]
            or 0
        )
        total_offers_accepted = (
            all_recruitments.aggregate(total=Coalesce(Sum("offers_accepted"), 0))[
                "total"
            ]
            or 0
        )

        # Ensure we have integers
        total_applications = int(total_applications) if total_applications else 0
        total_interviews = int(total_interviews) if total_interviews else 0
        total_offers_made = int(total_offers_made) if total_offers_made else 0
        total_offers_accepted = (
            int(total_offers_accepted) if total_offers_accepted else 0
        )

        # Calculate percentages and conversion rates
        applications_percentage = Decimal("100.00")  # Base: 100%

        interviews_percentage = (
            (
                Decimal(str(total_interviews))
                / Decimal(str(total_applications))
                * Decimal("100")
            )
            if total_applications > 0
            else Decimal("0.00")
        )
        interviews_conversion = interviews_percentage  # From applications

        offers_percentage = (
            (
                Decimal(str(total_offers_made))
                / Decimal(str(total_applications))
                * Decimal("100")
            )
            if total_applications > 0
            else Decimal("0.00")
        )
        offers_conversion = (
            (
                Decimal(str(total_offers_made))
                / Decimal(str(total_interviews))
                * Decimal("100")
            )
            if total_interviews > 0
            else Decimal("0.00")
        )

        accepted_percentage = (
            (
                Decimal(str(total_offers_accepted))
                / Decimal(str(total_applications))
                * Decimal("100")
            )
            if total_applications > 0
            else Decimal("0.00")
        )
        acceptance_conversion = (
            (
                Decimal(str(total_offers_accepted))
                / Decimal(str(total_offers_made))
                * Decimal("100")
            )
            if total_offers_made > 0
            else Decimal("0.00")
        )

        return {
            "applications_received": total_applications,
            "applications_received_percentage": applications_percentage.quantize(
                Decimal("0.1")
            ),
            "interviews_conducted": total_interviews,
            "interviews_conducted_percentage": interviews_percentage.quantize(
                Decimal("0.1")
            ),
            "interviews_conversion_rate": interviews_conversion.quantize(
                Decimal("0.1")
            ),
            "offers_made": total_offers_made,
            "offers_made_percentage": offers_percentage.quantize(Decimal("0.1")),
            "offers_conversion_rate": offers_conversion.quantize(Decimal("0.1")),
            "offers_accepted": total_offers_accepted,
            "offers_accepted_percentage": accepted_percentage.quantize(Decimal("0.1")),
            "acceptance_conversion_rate": acceptance_conversion.quantize(
                Decimal("0.1")
            ),
        }

    def _calculate_source_effectiveness(self, all_recruitments):
        """Calculate source effectiveness breakdown"""
        # Group by source
        source_data = (
            all_recruitments.filter(source__isnull=False)
            .values("source")
            .annotate(
                total_applications=Coalesce(Sum("applications_received"), 0),
                total_hires=Coalesce(Sum("offers_accepted"), 0),
                total_cost=Coalesce(Sum("cost_spent"), Decimal("0.00")),
            )
        )

        source_effectiveness = []

        for item in source_data:
            source = item["source"]
            applications = item["total_applications"] or 0
            hires = item["total_hires"] or 0
            total_cost = item["total_cost"] or Decimal("0.00")

            # Calculate conversion percentage
            conversion_percentage = (
                (Decimal(str(hires)) / Decimal(str(applications)) * Decimal("100"))
                if applications > 0
                else Decimal("0.00")
            )

            # Calculate cost per hire
            cost_per_hire = (
                total_cost / Decimal(str(hires)) if hires > 0 else Decimal("0.00")
            )

            source_effectiveness.append(
                {
                    "source": source,
                    "applications": applications,
                    "hires": hires,
                    "conversion_percentage": conversion_percentage.quantize(
                        Decimal("0.1")
                    ),
                    "cost_per_hire": cost_per_hire.quantize(Decimal("0.01")),
                    "cost_per_hire_display": self._format_cost(cost_per_hire),
                }
            )

        # Sort by applications descending
        source_effectiveness.sort(key=lambda x: x["applications"], reverse=True)

        return source_effectiveness

    def _get_open_positions(self, company):
        """Get list of open positions"""
        open_recruitments = (
            Recruitment.objects.filter(
                company=company,
                status__in=[
                    RecruitmentStatusChoices.OPEN,
                    RecruitmentStatusChoices.IN_PROGRESS,
                ],
            )
            .select_related("department")
            .order_by("-posting_date")
        )

        open_positions = []

        for rec in open_recruitments:
            open_positions.append(
                {
                    "job_title": rec.job_title,
                    "department": rec.department.name if rec.department else None,
                    "positions": rec.positions_required,
                    "applications": rec.applications_received,
                    "status": rec.status,
                    "status_display": rec.get_status_display(),
                }
            )

        return open_positions

    def _format_cost(self, cost: Decimal) -> str:
        """Format cost in Indian Rupees with K notation"""
        if cost == 0:
            return "₹0.00K"
        if cost >= 1000:
            return f"₹{(cost / Decimal('1000')).quantize(Decimal('0.01'))}K"
        return f"₹{cost.quantize(Decimal('0.01'))}"
