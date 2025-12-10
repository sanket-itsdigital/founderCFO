from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timedelta
from calendar import month_abbr

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.forecast import SalesForecastSerializer
from sales.views.api.utils import get_company_from_request


class SalesForecastView(APIView):
    """
    Sales Forecast API
    Returns forecast summary cards, waterfall chart, monthly breakdown, and pipeline coverage
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
            return SalesForecastView._in_crores(amount)
        else:
            return SalesForecastView._in_lakhs(amount)

    @staticmethod
    def _get_quarter_info(period):
        """Get quarter information from period string (e.g., 'Q4 FY25')"""
        # Default to current quarter
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month
        
        if current_month <= 3:
            quarter = 1
        elif current_month <= 6:
            quarter = 2
        elif current_month <= 9:
            quarter = 3
        else:
            quarter = 4
        
        # Parse period if provided
        if period:
            if "Q" in period.upper():
                try:
                    q_part = period.upper().split("Q")[1].split()[0]
                    quarter = int(q_part)
                except (IndexError, ValueError):
                    pass
        
        # Calculate quarter dates
        if quarter == 1:
            start_date = datetime(current_year, 1, 1).date()
            end_date = datetime(current_year, 3, 31).date()
        elif quarter == 2:
            start_date = datetime(current_year, 4, 1).date()
            end_date = datetime(current_year, 6, 30).date()
        elif quarter == 3:
            start_date = datetime(current_year, 7, 1).date()
            end_date = datetime(current_year, 9, 30).date()
        else:
            start_date = datetime(current_year, 10, 1).date()
            end_date = datetime(current_year, 12, 31).date()
        
        return f"Q{quarter} FY{str(current_year)[-2:]}", start_date, end_date

    def _categorize_deal(self, deal):
        """Categorize deal into commit, best_case, pipeline, or upside"""
        if deal.stage == SalesStageStatusChoices.CLOSED_WON:
            return "closed"
        elif deal.probability >= 75:
            return "commit"
        elif deal.probability >= 50:
            return "best_case"
        elif deal.probability >= 25:
            return "pipeline"
        else:
            return "upside"

    def get(self, request):
        """Get Sales Forecast data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period (default to current quarter)
        period = request.query_params.get("period", None)
        period_name, start_date, end_date = SalesForecastView._get_quarter_info(period)

        # Get all sales for the period
        all_sales = Sales.objects.filter(company=company)
        closed_sales = all_sales.filter(
            stage=SalesStageStatusChoices.CLOSED_WON,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        
        open_sales = all_sales.exclude(stage__in=[
            SalesStageStatusChoices.CLOSED_WON,
            SalesStageStatusChoices.CLOSED_LOST,
        ]).filter(close_date__gte=start_date, close_date__lte=end_date)

        # Calculate closed amount
        closed_amount = sum(deal.amount for deal in closed_sales) or Decimal("0.00")

        # Calculate forecast categories
        commit_deals = [d for d in open_sales if self._categorize_deal(d) == "commit"]
        best_case_deals = [d for d in open_sales if self._categorize_deal(d) == "best_case"]
        pipeline_deals = [d for d in open_sales if self._categorize_deal(d) == "pipeline"]
        upside_deals = [d for d in open_sales if self._categorize_deal(d) == "upside"]

        commit_amount = sum(deal.amount for deal in commit_deals) or Decimal("0.00")
        best_case_amount = sum(deal.amount for deal in best_case_deals) or Decimal("0.00")
        pipeline_amount = sum(deal.amount for deal in pipeline_deals) or Decimal("0.00")

        # Calculate quota (can be configured per company, defaulting to sum of all)
        quota = closed_amount + commit_amount + best_case_amount + pipeline_amount
        gap_to_quota = quota - (closed_amount + commit_amount)

        # Summary Cards
        summary_cards = [
            {
                "title": "Quota",
                "value": float(quota),
                "value_display": self._format_amount_display(quota),
                "subtitle": period_name,
                "icon": "target",
            },
            {
                "title": "Closed",
                "value": float(closed_amount),
                "value_display": self._format_amount_display(closed_amount),
                "subtitle": f"{(closed_amount / quota * 100).quantize(Decimal('0.01'))}% of quota" if quota > 0 else "0% of quota",
                "icon": "checkmark",
            },
            {
                "title": "Commit",
                "value": float(commit_amount),
                "value_display": self._format_amount_display(commit_amount),
                "subtitle": "High confidence",
                "icon": "trend-up",
            },
            {
                "title": "Best Case",
                "value": float(best_case_amount),
                "value_display": self._format_amount_display(best_case_amount),
                "subtitle": "60%+ probability",
                "icon": "bar-chart",
            },
            {
                "title": "Gap to Quota",
                "value": float(gap_to_quota),
                "value_display": self._format_amount_display(gap_to_quota),
                "subtitle": f"{(gap_to_quota / quota * 100).quantize(Decimal('0.01'))}% gap remaining" if quota > 0 else "0% gap remaining",
                "icon": "warning",
            },
        ]

        # Forecast Waterfall
        cumulative = closed_amount
        waterfall_data = [
            {
                "category": "Closed",
                "value": float(closed_amount),
                "value_display": self._format_amount_display(closed_amount),
                "cumulative_value": float(cumulative),
                "cumulative_value_display": self._format_amount_display(cumulative),
            },
        ]
        
        cumulative += commit_amount
        waterfall_data.append({
            "category": "Commit",
            "value": float(commit_amount),
            "value_display": self._format_amount_display(commit_amount),
            "cumulative_value": float(cumulative),
            "cumulative_value_display": self._format_amount_display(cumulative),
        })
        
        cumulative += best_case_amount
        waterfall_data.append({
            "category": "Best Case",
            "value": float(best_case_amount),
            "value_display": self._format_amount_display(best_case_amount),
            "cumulative_value": float(cumulative),
            "cumulative_value_display": self._format_amount_display(cumulative),
        })
        
        cumulative += pipeline_amount
        waterfall_data.append({
            "category": "Pipeline",
            "value": float(pipeline_amount),
            "value_display": self._format_amount_display(pipeline_amount),
            "cumulative_value": float(cumulative),
            "cumulative_value_display": self._format_amount_display(cumulative),
        })

        # Monthly Breakdown
        monthly_data = defaultdict(lambda: {
            "closed": Decimal("0.00"),
            "commit": Decimal("0.00"),
            "best_case": Decimal("0.00"),
            "pipeline": Decimal("0.00"),
        })

        for deal in closed_sales:
            month_key = deal.created_at.strftime("%b %Y")
            monthly_data[month_key]["closed"] += deal.amount

        for deal in open_sales:
            if deal.close_date:
                month_key = deal.close_date.strftime("%b %Y")
                category = self._categorize_deal(deal)
                if category in ["commit", "best_case", "pipeline"]:
                    monthly_data[month_key][category] += deal.amount

        monthly_breakdown_data = []
        sorted_months = sorted(monthly_data.keys())
        for month in sorted_months:
            data = monthly_data[month]
            total = data["closed"] + data["commit"] + data["best_case"] + data["pipeline"]
            monthly_breakdown_data.append({
                "month": month,
                "closed": float(data["closed"]),
                "closed_display": self._format_amount_display(data["closed"]),
                "commit": float(data["commit"]),
                "commit_display": self._format_amount_display(data["commit"]),
                "best_case": float(data["best_case"]),
                "best_case_display": self._format_amount_display(data["best_case"]),
                "pipeline": float(data["pipeline"]),
                "pipeline_display": self._format_amount_display(data["pipeline"]),
                "total": float(total),
                "total_display": self._format_amount_display(total),
            })

        # Pipeline Coverage
        total_pipeline = commit_amount + best_case_amount + pipeline_amount
        coverage_multiplier = (total_pipeline / quota).quantize(Decimal("0.1")) if quota > 0 else Decimal("0.0")
        
        coverage_cards = [
            {
                "category": "Commit",
                "value": float(commit_amount),
                "value_display": self._format_amount_display(commit_amount),
                "deals": len(commit_deals),
                "weighted_value": float(commit_amount * Decimal("0.8")),  # 80% weight
                "weighted_value_display": self._format_amount_display(commit_amount * Decimal("0.8")),
            },
            {
                "category": "Best Case",
                "value": float(best_case_amount),
                "value_display": self._format_amount_display(best_case_amount),
                "deals": len(best_case_deals),
                "weighted_value": float(best_case_amount * Decimal("0.6")),  # 60% weight
                "weighted_value_display": self._format_amount_display(best_case_amount * Decimal("0.6")),
            },
            {
                "category": "Pipeline",
                "value": float(pipeline_amount),
                "value_display": self._format_amount_display(pipeline_amount),
                "deals": len(pipeline_deals),
                "weighted_value": float(pipeline_amount * Decimal("0.4")),  # 40% weight
                "weighted_value_display": self._format_amount_display(pipeline_amount * Decimal("0.4")),
            },
            {
                "category": "Upside",
                "value": float(sum(deal.amount for deal in upside_deals) or Decimal("0.00")),
                "value_display": self._format_amount_display(sum(deal.amount for deal in upside_deals) or Decimal("0.00")),
                "deals": len(upside_deals),
                "weighted_value": float(sum(deal.amount for deal in upside_deals) * Decimal("0.2") or Decimal("0.00")),  # 20% weight
                "weighted_value_display": self._format_amount_display(sum(deal.amount for deal in upside_deals) * Decimal("0.2") or Decimal("0.00")),
            },
        ]

        response_data = {
            "period": period_name,
            "summary_cards": summary_cards,
            "forecast_waterfall": {
                "title": "Forecast Waterfall",
                "subtitle": "Path to quota achievement",
                "data": waterfall_data,
                "quota": float(quota),
                "quota_display": self._format_amount_display(quota),
            },
            "monthly_breakdown": {
                "title": "Monthly Breakdown",
                "subtitle": "Expected close by month",
                "data": monthly_breakdown_data,
            },
            "pipeline_coverage": {
                "title": "Pipeline Coverage Analysis",
                "coverage_multiplier": float(coverage_multiplier),
                "coverage_display": f"{coverage_multiplier}x Coverage",
                "cards": coverage_cards,
            },
        }

        serializer = SalesForecastSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

