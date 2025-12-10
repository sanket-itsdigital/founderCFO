from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales, SalesTeam
from sales.enums import SalesStageStatusChoices
from sales.serializers.sales_overview import SalesOverviewSerializer
from sales.views.api.utils import get_company_from_request


class SalesOverviewView(APIView):
    """
    Sales Overview API
    Returns comprehensive sales dashboard data including summary cards, pipeline health, KPIs, funnel, and leaderboard
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
            return SalesOverviewView._in_crores(amount)
        else:
            return SalesOverviewView._in_lakhs(amount)

    def _get_date_range(self, period):
        """Get date range based on period filter"""
        today = timezone.now().date()

        if period == "7":
            start_date = today - timedelta(days=7)
        elif period == "30":
            start_date = today - timedelta(days=30)
        elif period == "90":
            start_date = today - timedelta(days=90)
        elif period == "365" or period == "year":
            start_date = today - timedelta(days=365)
        elif period == "quarter":
            # Current quarter
            current_month = today.month
            if current_month <= 3:
                start_date = datetime(today.year, 1, 1).date()
            elif current_month <= 6:
                start_date = datetime(today.year, 4, 1).date()
            elif current_month <= 9:
                start_date = datetime(today.year, 7, 1).date()
            else:
                start_date = datetime(today.year, 10, 1).date()
        else:
            # Default to 30 days
            start_date = today - timedelta(days=30)

        return start_date, today

    def _calculate_sales_velocity(self, company, start_date, end_date):
        """Calculate average sales velocity (days to close)"""
        closed_deals = Sales.objects.filter(
            company=company,
            stage=SalesStageStatusChoices.CLOSED_WON,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            close_date__isnull=False,
        )

        if not closed_deals.exists():
            return None

        total_days = 0
        count = 0
        for deal in closed_deals:
            if deal.created_at and deal.close_date:
                days = (deal.close_date - deal.created_at.date()).days
                if days > 0:
                    total_days += days
                    count += 1

        if count == 0:
            return None

        return Decimal(total_days) / Decimal(count)

    def get(self, request):
        """Get Sales Overview data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        # Get all sales
        all_sales = Sales.objects.filter(company=company)
        period_sales = all_sales.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        # Calculate closed amount
        closed_deals = period_sales.filter(stage=SalesStageStatusChoices.CLOSED_WON)
        closed_amount = sum(deal.amount for deal in closed_deals) or Decimal("0.00")

        # Get open deals (not closed won/lost)
        open_deals = all_sales.exclude(
            stage__in=[
                SalesStageStatusChoices.CLOSED_WON,
                SalesStageStatusChoices.CLOSED_LOST,
            ]
        )

        # Calculate commit (high probability deals)
        commit_deals = [d for d in open_deals if d.probability >= 75]
        commit_amount = sum(deal.amount for deal in commit_deals) or Decimal("0.00")

        # Calculate best case (medium-high probability deals)
        best_case_deals = [d for d in open_deals if 50 <= d.probability < 75]
        best_case_amount = sum(deal.amount for deal in best_case_deals) or Decimal(
            "0.00"
        )

        # Calculate quota (closed + commit + best case)
        quota = closed_amount + commit_amount + best_case_amount
        if quota == 0:
            quota = Decimal("31000000")  # Default 3.1Cr

        # Calculate gap
        gap = quota - (closed_amount + commit_amount)

        # Summary Cards
        summary_cards = [
            {
                "title": "Quota",
                "value": float(quota),
                "value_display": self._format_amount_display(quota),
                "subtitle": "",
                "icon": "target",
            },
            {
                "title": "Closed",
                "value": float(closed_amount),
                "value_display": self._format_amount_display(closed_amount),
                "subtitle": (
                    f"{(closed_amount / quota * 100).quantize(Decimal('0'))}%"
                    if quota > 0
                    else "0%"
                ),
                "icon": "checkmark",
            },
            {
                "title": "Commit",
                "value": float(commit_amount),
                "value_display": self._format_amount_display(commit_amount),
                "subtitle": (
                    f"{(commit_amount / quota * 100).quantize(Decimal('0'))}%"
                    if quota > 0
                    else "0%"
                ),
                "icon": "trend-up",
            },
            {
                "title": "Best Case",
                "value": float(best_case_amount),
                "value_display": self._format_amount_display(best_case_amount),
                "subtitle": "",
                "icon": "trend-up",
            },
        ]

        # Gap card (separate)
        gap_card = {
            "title": "Gap",
            "value": float(gap),
            "value_display": self._format_amount_display(gap),
            "subtitle": "",
            "icon": "warning",
            "gap": float(gap),
            "gap_display": self._format_amount_display(gap),
        }

        # Pipeline Health
        pipeline_value = sum(deal.amount for deal in open_deals) or Decimal("0.00")
        open_deals_count = open_deals.count()

        # Calculate average velocity (days in stage for open deals)
        avg_velocity = None
        if open_deals.exists():
            total_days = sum(
                deal.days_in_stage for deal in open_deals if deal.days_in_stage
            )
            count = sum(1 for deal in open_deals if deal.days_in_stage)
            if count > 0:
                avg_velocity = Decimal(total_days) / Decimal(count)

        # Stalled deals (deals with no activity for 30+ days or days_in_stage > 30)
        stalled_deals = [
            d
            for d in open_deals
            if d.days_in_stage > 30
            or (d.last_activity and (timezone.now().date() - d.last_activity).days > 30)
        ]
        stalled_count = len(stalled_deals)
        stalled_amount = sum(deal.amount for deal in stalled_deals) or Decimal("0.00")
        critical_count = sum(1 for d in stalled_deals if d.probability >= 50)

        # Calculate pipeline health score (0-100)
        # Based on: pipeline coverage, deal velocity, stalled deals
        health_score = 72  # Default moderate
        if pipeline_value > 0 and quota > 0:
            coverage_ratio = (pipeline_value / quota).quantize(Decimal("0.01"))
            if coverage_ratio >= Decimal("2.0"):
                health_score = 90
            elif coverage_ratio >= Decimal("1.5"):
                health_score = 75
            elif coverage_ratio >= Decimal("1.0"):
                health_score = 60
            else:
                health_score = 45

        # Adjust based on stalled deals
        if stalled_count > 0:
            stalled_ratio = (
                stalled_amount / pipeline_value if pipeline_value > 0 else Decimal("0")
            )
            if stalled_ratio > Decimal("0.2"):  # More than 20% stalled
                health_score = max(40, health_score - 15)
            elif stalled_ratio > Decimal("0.1"):  # More than 10% stalled
                health_score = max(50, health_score - 10)

        health_status = (
            "Excellent"
            if health_score >= 80
            else (
                "Good"
                if health_score >= 60
                else "Moderate" if health_score >= 40 else "Poor"
            )
        )

        pipeline_health = {
            "health_score": health_score,
            "health_status": health_status,
            "open_deals": open_deals_count,
            "pipeline_value": float(pipeline_value),
            "pipeline_value_display": self._format_amount_display(pipeline_value),
            "avg_velocity": float(avg_velocity) if avg_velocity else None,
            "avg_velocity_display": (
                f"{avg_velocity.quantize(Decimal('0.1'))} days"
                if avg_velocity
                else "N/A"
            ),
            "stalled_deals": stalled_count,
            "stalled_amount": float(stalled_amount) if stalled_amount > 0 else None,
            "stalled_amount_display": (
                self._format_amount_display(stalled_amount)
                if stalled_amount > 0
                else None
            ),
            "critical_count": critical_count,
        }

        # KPI Cards
        # Total Revenue (ARR) - Annual Recurring Revenue
        total_mrr = sum(
            deal.mrr
            for deal in all_sales.filter(stage=SalesStageStatusChoices.CLOSED_WON)
        ) or Decimal("0.00")
        arr = total_mrr * Decimal("12")

        # Current MRR
        current_mrr = sum(
            deal.mrr
            for deal in period_sales.filter(stage=SalesStageStatusChoices.CLOSED_WON)
        ) or Decimal("0.00")

        # Win Rate
        total_deals = period_sales.count()
        won_deals = closed_deals.count()
        win_rate = (
            (Decimal(won_deals) / Decimal(total_deals) * 100)
            if total_deals > 0
            else Decimal("0.00")
        )

        # Sales Velocity
        sales_velocity = self._calculate_sales_velocity(company, start_date, end_date)

        # Average Deal Size
        avg_deal_size = (
            (closed_amount / won_deals) if won_deals > 0 else Decimal("0.00")
        )

        # Pipeline Coverage
        pipeline_coverage = (
            (pipeline_value / quota).quantize(Decimal("0.1"))
            if quota > 0
            else Decimal("0.0")
        )

        kpi_cards = [
            {
                "title": "Total Revenue (ARR)",
                "value": str(float(arr)),
                "value_display": self._format_amount_display(arr),
                "subtitle": "Annual Recurring Revenue",
                "icon": "dollar",
                "icon_color": "blue",
            },
            {
                "title": "Monthly Recurring Revenue",
                "value": str(float(current_mrr)),
                "value_display": self._format_amount_display(current_mrr),
                "subtitle": "MRR growth trajectory",
                "icon": "trend-up",
                "icon_color": "green",
            },
            {
                "title": "Win Rate",
                "value": str(float(win_rate)),
                "value_display": f"{win_rate.quantize(Decimal('0.1'))}%",
                "subtitle": "Opportunities closed won",
                "icon": "target",
                "icon_color": "purple",
            },
            {
                "title": "Sales Velocity",
                "value": str(float(sales_velocity)) if sales_velocity else "N/A",
                "value_display": (
                    f"{sales_velocity.quantize(Decimal('0.1'))} days"
                    if sales_velocity
                    else "N/A"
                ),
                "subtitle": "Daily revenue generation rate",
                "icon": "trend-up",
                "icon_color": "green",
            },
            {
                "title": "Average Deal Size",
                "value": str(float(avg_deal_size)),
                "value_display": self._format_amount_display(avg_deal_size),
                "subtitle": "Mean contract value",
                "icon": "dollar",
                "icon_color": "pink",
            },
            {
                "title": "Pipeline Coverage",
                "value": str(float(pipeline_coverage)),
                "value_display": f"{pipeline_coverage}x",
                "subtitle": "Pipeline vs quarterly target",
                "icon": "bar-chart",
                "icon_color": "purple",
            },
        ]

        # Sales Funnel (Dynamic - based on period or all time based on query param)
        use_period_for_funnel = (
            request.query_params.get("funnel_period", "false").lower() == "true"
        )
        funnel_sales = period_sales if use_period_for_funnel else all_sales

        funnel_stages = [
            SalesStageStatusChoices.DISCOVERY,
            SalesStageStatusChoices.QUALIFICATION,
            SalesStageStatusChoices.PROPOSAL,
            SalesStageStatusChoices.NEGOTIATION,
            SalesStageStatusChoices.CLOSED_WON,
        ]

        sales_funnel = []
        for stage in funnel_stages:
            stage_deals = funnel_sales.filter(stage=stage)
            stage_amount = sum(deal.amount for deal in stage_deals) or Decimal("0.00")
            deals_count = stage_deals.count()

            # Only include stages with deals (dynamic - only show if has value)
            if deals_count > 0 or stage_amount > 0:
                sales_funnel.append(
                    {
                        "stage": stage,
                        "deals_count": deals_count,
                        "amount": float(stage_amount),
                        "amount_display": self._format_amount_display(stage_amount),
                    }
                )

        # Sales Leaderboard (Dynamic - based on period)
        # Get leaderboard limit from query params (default 5)
        leaderboard_limit = int(request.query_params.get("leaderboard_limit", 5))

        sales_teams = SalesTeam.objects.filter(company=company, is_active=True)
        leaderboard_data = []

        for team in sales_teams:
            # Use period-based closed deals for leaderboard
            rep_deals = closed_deals.filter(sales_team=team)
            deals_closed = rep_deals.count()
            revenue = sum(deal.amount for deal in rep_deals) or Decimal("0.00")

            # Calculate quota attainment (use period-based data)
            rep_open_deals = open_deals.filter(sales_team=team)
            rep_commit_deals = [d for d in rep_open_deals if d.probability >= 75]
            rep_commit_amount = sum(
                deal.amount for deal in rep_commit_deals
            ) or Decimal("0.00")

            rep_quota = revenue + rep_commit_amount
            if rep_quota == 0:
                rep_quota = Decimal("5000000")  # Default 50L

            quota_attainment = (
                (revenue / rep_quota * 100) if rep_quota > 0 else Decimal("0.00")
            )

            # Only include reps with deals
            if deals_closed > 0 or revenue > 0:
                leaderboard_data.append(
                    {
                        "rep_name": team.name,
                        "deals_closed": deals_closed,
                        "revenue": float(revenue),
                        "revenue_display": self._format_amount_display(revenue),
                        "quota_attainment": float(quota_attainment),
                        "quota_attainment_display": f"{quota_attainment.quantize(Decimal('0'))}%",
                    }
                )

        # Sort by quota attainment descending
        leaderboard_data.sort(key=lambda x: x["quota_attainment"], reverse=True)

        # Add rank
        for idx, rep in enumerate(leaderboard_data, 1):
            rep["rank"] = idx

        # Limit to requested number (default 5)
        sales_leaderboard = leaderboard_data[:leaderboard_limit]

        # Pipeline Overview (Dynamic - with filters)
        stage_filter = request.query_params.get("pipeline_stage", None)
        search_query = request.query_params.get("pipeline_search", None)
        pipeline_limit = int(request.query_params.get("pipeline_limit", 10))

        pipeline_deals = all_sales.select_related("sales_team").order_by("-created_at")

        # Apply stage filter
        if stage_filter and stage_filter != "All Stages":
            pipeline_deals = pipeline_deals.filter(stage=stage_filter)

        # Apply search filter
        if search_query:
            pipeline_deals = pipeline_deals.filter(
                Q(deal_name__icontains=search_query)
                | Q(client__icontains=search_query)
                | Q(deal_id__icontains=search_query)
                | Q(sales_team__name__icontains=search_query)
            )

        # Limit results
        pipeline_deals = pipeline_deals[:pipeline_limit]

        pipeline_deals_data = []
        for deal in pipeline_deals:
            # Determine status based on stage
            if deal.stage == SalesStageStatusChoices.CLOSED_WON:
                deal_status = "Won"
            elif deal.stage == SalesStageStatusChoices.CLOSED_LOST:
                deal_status = "Lost"
            else:
                deal_status = "Open"

            pipeline_deals_data.append(
                {
                    "deal_id": str(deal.id),
                    "account_name": deal.client,
                    "owner": deal.sales_team.name if deal.sales_team else "Unassigned",
                    "product": deal.subscription_product or "",
                    "amount": float(deal.amount),
                    "amount_display": self._format_amount_display(deal.amount),
                    "mrr": float(deal.mrr),
                    "mrr_display": self._format_amount_display(deal.mrr),
                    "stage": deal.stage,
                    "probability": float(deal.probability),
                    "probability_display": f"{deal.probability.quantize(Decimal('0'))}%",
                    "close_date": deal.close_date,
                    "close_date_display": (
                        deal.close_date.strftime("%d %b %Y") if deal.close_date else ""
                    ),
                    "status": deal_status,
                }
            )

        pipeline_overview = {
            "title": "Pipeline Overview",
            "deals": pipeline_deals_data,
            "total_count": all_sales.count(),
            "filtered_count": len(pipeline_deals_data),
        }

        response_data = {
            "summary_cards": summary_cards,
            "gap_card": gap_card,
            "pipeline_health": pipeline_health,
            "kpi_cards": kpi_cards,
            "sales_funnel": sales_funnel,
            "sales_leaderboard": sales_leaderboard,
            "pipeline_overview": pipeline_overview,
        }

        serializer = SalesOverviewSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
