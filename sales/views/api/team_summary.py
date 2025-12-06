from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales, SalesTeam
from sales.enums import SalesStageStatusChoices
from sales.serializers.team_summary import TeamSummaryCardsSerializer
from sales.views.api.utils import get_company_from_request


class TeamSummaryView(APIView):
    """
    Team Summary Cards API
    Returns summary cards: Top Performer, Team Avg Attainment, Total Deals Closed, Reps At/Above Quota
    """

    permission_classes = [IsAuthenticated]

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

    def get(self, request):
        """Get Team Summary Cards data"""
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

        reps_attainment = []
        total_deals_closed = 0
        top_performer_name = None
        top_performer_attainment = Decimal("0.00")

        for team in sales_teams:
            # Get all sales for this rep in the period
            rep_sales = Sales.objects.filter(
                company=company,
                sales_team=team,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )

            # Calculate quota and achieved
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
            reps_attainment.append(float(attainment))

            # Track top performer
            if attainment > top_performer_attainment:
                top_performer_attainment = attainment
                top_performer_name = team.name

            # Count deals closed
            total_deals_closed += closed_deals.count()

        # Calculate team average attainment
        team_avg_attainment = (
            sum(reps_attainment) / len(reps_attainment) if reps_attainment else Decimal("0.00")
        )

        # Count reps at/above quota (attainment >= 100%)
        reps_at_above_quota = sum(1 for att in reps_attainment if att >= 100)
        total_reps = len(reps_attainment)
        success_rate = (reps_at_above_quota / total_reps * 100) if total_reps > 0 else Decimal("0.00")

        # Determine if team avg is below target
        is_below_target = team_avg_attainment < 100

        response_data = {
            "top_performer": {
                "title": "Top Performer",
                "name": top_performer_name or "N/A",
                "detail": f"{top_performer_attainment.quantize(Decimal('0'))}% quota attainment" if top_performer_name else "No data",
            },
            "team_avg_attainment": {
                "title": "Team Avg Attainment",
                "percentage": float(team_avg_attainment),
                "percentage_display": f"{team_avg_attainment.quantize(Decimal('0'))}%",
                "status": "Below target" if is_below_target else "On target",
            },
            "total_deals_closed": {
                "title": "Total Deals Closed",
                "count": total_deals_closed,
                "count_display": str(total_deals_closed),
                "period": "This period",
            },
            "reps_at_above_quota": {
                "title": "Reps At/Above Quota",
                "count": f"{reps_at_above_quota}/{total_reps}",
                "count_display": f"{reps_at_above_quota}/{total_reps}",
                "success_rate": f"{success_rate.quantize(Decimal('0'))}% success rate",
            },
        }

        serializer = TeamSummaryCardsSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

