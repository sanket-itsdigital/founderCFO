from decimal import Decimal
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.forecast_deal_detail import ForecastDealDetailResponseSerializer
from sales.views.api.utils import get_company_from_request
from sales.views.api.forecast import SalesForecastView


class ForecastDealDetailView(APIView):
    """
    Forecast Deal Detail API
    Returns all open deals with forecast category and risk assessment
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _categorize_deal(self, deal):
        """Categorize deal into commit, best_case, pipeline, or upside"""
        if deal.probability >= 75:
            return "commit"
        elif deal.probability >= 50:
            return "best_case"
        elif deal.probability >= 25:
            return "pipeline"
        else:
            return "upside"

    def _get_confidence(self, deal):
        """Get confidence level based on probability"""
        if deal.probability >= 75:
            return "high"
        elif deal.probability >= 50:
            return "medium"
        else:
            return "low"

    def _calculate_risk(self, deal):
        """Calculate risk level (1-3) based on days in stage and probability"""
        risk = 1
        if deal.days_in_stage > 30:
            risk += 1
        if deal.probability < 50:
            risk += 1
        return min(risk, 3)

    def get(self, request):
        """Get Forecast Deal Detail data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period
        period = request.query_params.get("period", None)
        period_name, start_date, end_date = SalesForecastView._get_quarter_info(period)

        # Get all open deals (not closed won/lost) with close dates in the period
        open_deals = Sales.objects.filter(
            company=company,
        ).exclude(
            stage__in=[
                SalesStageStatusChoices.CLOSED_WON,
                SalesStageStatusChoices.CLOSED_LOST,
            ]
        ).filter(
            close_date__gte=start_date,
            close_date__lte=end_date,
        ).select_related("sales_team")

        deals_data = []
        for deal in open_deals:
            category = self._categorize_deal(deal)
            confidence = self._get_confidence(deal)
            risk = self._calculate_risk(deal)
            
            deals_data.append({
                "account": deal.client,
                "owner": deal.sales_team.name if deal.sales_team else "Unassigned",
                "amount": float(deal.amount),
                "amount_display": self._in_lakhs(deal.amount),
                "stage": deal.stage,
                "category": category,
                "confidence": confidence,
                "close_date": deal.close_date,
                "close_date_display": deal.close_date.strftime("%d %b") if deal.close_date else "",
                "risk": risk,
            })

        # Sort by amount descending
        deals_data.sort(key=lambda x: x["amount"], reverse=True)

        response_data = {
            "title": "Forecast Deal Detail",
            "subtitle": "All open deals with forecast category and risk assessment",
            "deals": deals_data,
        }

        serializer = ForecastDealDetailResponseSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

