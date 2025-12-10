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
from sales.serializers.team_performance import TeamPerformanceSerializer
from sales.views.api.utils import get_company_from_request


class TeamPerformanceView(APIView):
    """
    Team Performance API (Combined)
    Returns sales team performance overview and revenue by product line
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _in_crores(amount: Decimal) -> str:
        """Convert amount to crores format (₹XX.XXCr)"""
        if amount == 0:
            return "₹0.00Cr"
        crores = amount / Decimal("10000000")
        return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as L or Cr based on value"""
        if amount >= Decimal("10000000"):
            return TeamPerformanceView._in_crores(amount)
        else:
            return TeamPerformanceView._in_lakhs(amount)

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

    def _calculate_win_rate(self, rep_sales):
        """Calculate win rate for a rep"""
        total_deals = rep_sales.count()
        if total_deals == 0:
            return Decimal("0.00")

        won_deals = rep_sales.filter(stage=SalesStageStatusChoices.CLOSED_WON).count()
        return (Decimal(won_deals) / Decimal(total_deals)) * Decimal("100")

    def _calculate_pipeline_coverage(self, rep_sales, quota):
        """Calculate pipeline coverage multiplier"""
        if quota == 0:
            return Decimal("0.0")

        # Get open deals (not closed won/lost)
        open_deals = rep_sales.exclude(
            stage__in=[
                SalesStageStatusChoices.CLOSED_WON,
                SalesStageStatusChoices.CLOSED_LOST,
            ]
        )

        pipeline_value = sum(deal.amount for deal in open_deals) or Decimal("0.00")
        return (pipeline_value / quota).quantize(Decimal("0.1"))

    def _calculate_rating(self, attainment, win_rate, deals_count):
        """Calculate performance rating (1-5 stars)"""
        # Base rating on attainment (0-100% maps to 1-5 stars)
        base_rating = (attainment / Decimal("100")) * Decimal("5")

        # Adjust based on win rate
        if win_rate >= 80:
            adjustment = Decimal("0.5")
        elif win_rate >= 60:
            adjustment = Decimal("0.2")
        else:
            adjustment = Decimal("-0.2")

        # Adjust based on deal count (more deals = better)
        if deals_count >= 5:
            adjustment += Decimal("0.2")
        elif deals_count >= 3:
            adjustment += Decimal("0.1")

        rating = base_rating + adjustment
        # Clamp between 1.0 and 5.0
        rating = max(Decimal("1.0"), min(Decimal("5.0"), rating))
        return rating.quantize(Decimal("0.1"))

    def _calculate_yoy_growth(
        self, company, product, current_revenue, start_date, end_date
    ):
        """Calculate Year-over-Year growth for a product"""
        # Get same period last year
        last_year_start = datetime(
            start_date.year - 1, start_date.month, start_date.day
        ).date()
        last_year_end = datetime(end_date.year - 1, end_date.month, end_date.day).date()

        last_year_sales = Sales.objects.filter(
            company=company,
            subscription_product=product,
            stage=SalesStageStatusChoices.CLOSED_WON,
            created_at__date__gte=last_year_start,
            created_at__date__lte=last_year_end,
        )
        last_year_revenue = sum(deal.amount for deal in last_year_sales) or Decimal(
            "0.00"
        )

        if last_year_revenue == 0:
            return None

        growth = ((current_revenue - last_year_revenue) / last_year_revenue) * Decimal(
            "100"
        )
        return growth.quantize(Decimal("0"))

    def get(self, request):
        """Get Team Performance data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        # Get all active sales team members
        sales_teams = SalesTeam.objects.filter(company=company, is_active=True)

        reps_data = []
        for team in sales_teams:
            # Get all sales for this rep in the period
            rep_sales = Sales.objects.filter(
                company=company,
                sales_team=team,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )

            # Calculate quota (default to sum of closed + commit deals, or 50L if none)
            closed_deals = rep_sales.filter(stage=SalesStageStatusChoices.CLOSED_WON)
            closed_amount = sum(deal.amount for deal in closed_deals) or Decimal("0.00")

            # Get open deals with high probability (commit)
            open_deals = rep_sales.exclude(
                stage__in=[
                    SalesStageStatusChoices.CLOSED_WON,
                    SalesStageStatusChoices.CLOSED_LOST,
                ]
            )
            commit_deals = [d for d in open_deals if d.probability >= 75]
            commit_amount = sum(deal.amount for deal in commit_deals) or Decimal("0.00")

            # Quota is closed + commit, or default
            quota = closed_amount + commit_amount
            if quota == 0:
                quota = Decimal("5000000")  # Default 50L

            # Achieved amount (closed won)
            achieved = closed_amount

            # Attainment percentage
            attainment = (achieved / quota * 100) if quota > 0 else Decimal("0.00")

            # Deals count (closed won)
            deals_count = closed_deals.count()

            # Average deal size
            avg_deal_size = (
                (achieved / deals_count) if deals_count > 0 else Decimal("0.00")
            )

            # Win rate
            win_rate = self._calculate_win_rate(rep_sales)

            # Pipeline coverage
            pipeline = self._calculate_pipeline_coverage(rep_sales, quota)

            # Rating
            rating = self._calculate_rating(attainment, win_rate, deals_count)

            reps_data.append(
                {
                    "rep_id": str(team.id),
                    "rep_name": team.name,
                    "designation": team.designation if team.designation else None,
                    "quota": float(quota),
                    "quota_display": self._format_amount_display(quota),
                    "achieved": float(achieved),
                    "achieved_display": self._format_amount_display(achieved),
                    "attainment": float(attainment),
                    "attainment_display": f"{attainment.quantize(Decimal('0'))}%",
                    "deals": deals_count,
                    "avg_deal_size": float(avg_deal_size),
                    "avg_deal_size_display": self._format_amount_display(avg_deal_size),
                    "win_rate": float(win_rate),
                    "win_rate_display": f"{win_rate.quantize(Decimal('0'))}%",
                    "pipeline": float(pipeline),
                    "pipeline_display": f"{pipeline}x",
                    "rating": float(rating),
                    "rating_display": f"★ {rating}",
                }
            )

        # Sort by attainment descending
        reps_data.sort(key=lambda x: x["attainment"], reverse=True)

        response_data = {
            "title": "Sales Team Performance Overview",
            "subtitle": f"Performance metrics for {period} days period",
            "reps": reps_data,
        }

        serializer = TeamPerformanceSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
