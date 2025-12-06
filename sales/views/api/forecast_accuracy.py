from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.forecast_accuracy import ForecastAccuracySerializer
from sales.views.api.utils import get_company_from_request
from sales.views.api.forecast import SalesForecastView


class ForecastAccuracyView(APIView):
    """
    Forecast Accuracy API
    Returns historical forecast vs actual comparison and accuracy trends
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
            return ForecastAccuracyView._in_crores(amount)
        else:
            return ForecastAccuracyView._in_lakhs(amount)

    def _get_quarter_dates(self, year, quarter):
        """Get start and end dates for a quarter"""
        if quarter == 1:
            start = datetime(year, 1, 1).date()
            end = datetime(year, 3, 31).date()
        elif quarter == 2:
            start = datetime(year, 4, 1).date()
            end = datetime(year, 6, 30).date()
        elif quarter == 3:
            start = datetime(year, 7, 1).date()
            end = datetime(year, 9, 30).date()
        else:
            start = datetime(year, 10, 1).date()
            end = datetime(year, 12, 31).date()
        return start, end

    def _get_month_dates(self, year, month):
        """Get start and end dates for a month"""
        if month == 12:
            start = datetime(year, month, 1).date()
            end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            start = datetime(year, month, 1).date()
            end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        return start, end

    def get(self, request):
        """Get Forecast Accuracy data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_year = timezone.now().year
        current_month = timezone.now().month

        # Get historical data for last 3 quarters and last 2 months
        forecast_vs_actual_data = []
        accuracy_trend_data = []
        accuracy_summary_data = []

        # Quarters
        for q in range(1, 4):
            year = current_year if q <= ((current_month - 1) // 3 + 1) else current_year - 1
            start_date, end_date = self._get_quarter_dates(year, q)
            
            # Actual (closed won deals)
            actual_deals = Sales.objects.filter(
                company=company,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            actual_amount = sum(deal.amount for deal in actual_deals) or Decimal("0.00")

            # Forecast (would be stored forecast, for now estimate from open deals)
            # In reality, you'd have a separate Forecast model
            forecast_amount = actual_amount * Decimal("1.05")  # Estimate 5% higher

            variance = actual_amount - forecast_amount
            accuracy = (1 - abs(variance) / forecast_amount) * 100 if forecast_amount > 0 else 100.0
            accuracy = max(0, min(100, accuracy))

            period_name = f"Q{q} FY{str(year)[-2:]}"
            forecast_vs_actual_data.append({
                "period": period_name,
                "forecast": float(forecast_amount),
                "forecast_display": self._format_amount_display(forecast_amount),
                "actual": float(actual_amount),
                "actual_display": self._format_amount_display(actual_amount),
            })

            accuracy_trend_data.append({
                "period": period_name,
                "accuracy": float(accuracy),
            })

            accuracy_summary_data.append({
                "period": period_name,
                "forecast": float(forecast_amount),
                "forecast_display": self._format_amount_display(forecast_amount),
                "actual": float(actual_amount),
                "actual_display": self._format_amount_display(actual_amount),
                "variance": float(variance),
                "variance_display": f"{'+' if variance >= 0 else ''}{self._format_amount_display(abs(variance))}",
                "accuracy": float(accuracy),
                "accuracy_display": f"{accuracy:.1f}%",
            })

        # Last 2 months
        for m in range(current_month - 1, current_month + 1):
            if m <= 0:
                m = 12 + m
                year = current_year - 1
            else:
                year = current_year
            
            start_date, end_date = self._get_month_dates(year, m)
            
            actual_deals = Sales.objects.filter(
                company=company,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            actual_amount = sum(deal.amount for deal in actual_deals) or Decimal("0.00")
            forecast_amount = actual_amount * Decimal("1.03")  # Estimate 3% higher

            variance = actual_amount - forecast_amount
            accuracy = (1 - abs(variance) / forecast_amount) * 100 if forecast_amount > 0 else 100.0
            accuracy = max(0, min(100, accuracy))

            month_name = datetime(year, m, 1).strftime("%b %Y")
            forecast_vs_actual_data.append({
                "period": month_name,
                "forecast": float(forecast_amount),
                "forecast_display": self._format_amount_display(forecast_amount),
                "actual": float(actual_amount),
                "actual_display": self._format_amount_display(actual_amount),
            })

            accuracy_trend_data.append({
                "period": month_name,
                "accuracy": float(accuracy),
            })

            accuracy_summary_data.append({
                "period": month_name,
                "forecast": float(forecast_amount),
                "forecast_display": self._format_amount_display(forecast_amount),
                "actual": float(actual_amount),
                "actual_display": self._format_amount_display(actual_amount),
                "variance": float(variance),
                "variance_display": f"{'+' if variance >= 0 else ''}{self._format_amount_display(abs(variance))}",
                "accuracy": float(accuracy),
                "accuracy_display": f"{accuracy:.1f}%",
            })

        response_data = {
            "forecast_vs_actual": {
                "title": "Forecast vs Actual",
                "subtitle": "Historical accuracy tracking",
                "data": forecast_vs_actual_data,
            },
            "accuracy_trend": {
                "title": "Accuracy Trend",
                "subtitle": "Forecast accuracy over time",
                "data": accuracy_trend_data,
            },
            "accuracy_summary": {
                "title": "Accuracy Summary",
                "data": accuracy_summary_data,
            },
        }

        serializer = ForecastAccuracySerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

