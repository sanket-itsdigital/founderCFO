from collections import defaultdict
from decimal import Decimal
from datetime import timedelta
from calendar import month_abbr

from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.sales_performance import SalesPerformanceDashboardSerializer
from sales.views.api.utils import get_company_from_request


class SalesPerformanceDashboardView(APIView):
    """
    Sales Performance Dashboard API
    Returns summary metrics and ARR Growth Waterfall chart data
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
            return SalesPerformanceDashboardView._in_crores(amount)
        else:
            return SalesPerformanceDashboardView._in_lakhs(amount)

    def _get_date_range(self, period):
        """Get date range based on period filter"""
        today = timezone.now().date()
        if period == "7":
            start_date = today - timedelta(days=7)
        elif period == "30":
            start_date = today - timedelta(days=30)
        elif period == "90":
            start_date = today - timedelta(days=90)
        elif period == "year":
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)  # Default to 30 days
        return start_date, today

    def _calculate_arr_waterfall(self, company, start_date, end_date):
        """Calculate ARR Growth Waterfall by month"""
        # Get all sales in the date range
        sales = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).order_by("created_at")

        # Group by month
        monthly_data = defaultdict(lambda: {
            "new_revenue": Decimal("0.00"),
            "expansion": Decimal("0.00"),
            "churn": Decimal("0.00"),
        })

        for sale in sales:
            month_key = sale.created_at.strftime("%b")
            year_month = sale.created_at.strftime("%Y-%m")
            
            # Calculate ARR from MRR (multiply by 12)
            arr_value = sale.mrr * Decimal("12") if sale.mrr else Decimal("0.00")
            
            # Determine if it's new revenue, expansion, or churn based on stage
            if sale.stage == SalesStageStatusChoices.CLOSED_WON:
                # Check if this is a new customer or existing (expansion)
                # For simplicity, we'll consider it new revenue if it's the first deal
                # In a real scenario, you'd check customer history
                existing_deals = Sales.objects.filter(
                    company=company,
                    client=sale.client,
                    stage=SalesStageStatusChoices.CLOSED_WON,
                    created_at__lt=sale.created_at,
                ).exists()
                
                if existing_deals:
                    monthly_data[year_month]["expansion"] += arr_value
                else:
                    monthly_data[year_month]["new_revenue"] += arr_value
            elif sale.stage == SalesStageStatusChoices.CLOSED_LOST:
                # For churn, we need to check previous closed won deals
                # This is simplified - in reality, churn would be calculated differently
                monthly_data[year_month]["churn"] += arr_value

        # Convert to list and calculate total ARR
        waterfall_data = []
        running_total_arr = Decimal("0.00")
        
        # Sort months chronologically
        sorted_months = sorted(monthly_data.keys())
        
        for year_month in sorted_months:
            try:
                month_num = int(year_month.split("-")[1])
                month_name = month_abbr[month_num]
            except (IndexError, ValueError, KeyError):
                # Fallback if month parsing fails
                month_name = year_month
            
            new_rev = monthly_data[year_month]["new_revenue"]
            expansion = monthly_data[year_month]["expansion"]
            churn = monthly_data[year_month]["churn"]
            
            # Calculate total ARR (previous + new - churn)
            running_total_arr = running_total_arr + new_rev + expansion - churn
            
            waterfall_data.append({
                "month": month_name,
                "new_revenue": float(new_rev),
                "new_revenue_display": self._format_amount_display(new_rev),
                "expansion": float(expansion),
                "expansion_display": self._format_amount_display(expansion),
                "churn": float(churn),
                "churn_display": self._format_amount_display(churn),
                "total_arr": float(running_total_arr),
                "total_arr_display": self._format_amount_display(running_total_arr),
            })

        return waterfall_data

    def get(self, request):
        """Get Sales Performance Dashboard data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        # Calculate summary metrics
        total_deals = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).count()

        # Count unique sales team members
        unique_reps = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            sales_team__isnull=False,
        ).values("sales_team").distinct().count()

        # Count activities (using last_activity field)
        activities = Sales.objects.filter(
            company=company,
            last_activity__gte=start_date,
            last_activity__lte=end_date,
        ).count()

        # Calculate ARR Waterfall
        arr_waterfall_data = self._calculate_arr_waterfall(company, start_date, end_date)

        response_data = {
            "summary_metrics": {
                "deals": total_deals,
                "reps": unique_reps,
                "activities": activities,
            },
            "arr_waterfall": {
                "title": "ARR Growth Waterfall (By Month)",
                "data": arr_waterfall_data,
            },
        }

        serializer = SalesPerformanceDashboardSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

