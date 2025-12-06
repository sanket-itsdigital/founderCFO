from decimal import Decimal
from datetime import timedelta

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.arr_summary import ARRSummarySerializer
from sales.views.api.utils import get_company_from_request


class ARRSummaryView(APIView):
    """
    ARR Summary Cards API
    Returns New ARR, Expansion ARR, Churned ARR, and Net New ARR
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
            return ARRSummaryView._in_crores(amount)
        else:
            return ARRSummaryView._in_lakhs(amount)

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

    def get(self, request):
        """Get ARR Summary data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        # Calculate New ARR (closed won deals in period)
        new_arr_deals = Sales.objects.filter(
            company=company,
            stage=SalesStageStatusChoices.CLOSED_WON,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        
        new_arr_count = new_arr_deals.count()
        new_arr_total = sum(
            (deal.mrr * Decimal("12") if deal.mrr else Decimal("0.00"))
            for deal in new_arr_deals
        )

        # Calculate Expansion ARR (existing customers who upgraded)
        # This is simplified - in reality, you'd track customer history
        expansion_arr = Decimal("0.00")
        expansion_rate = Decimal("0.00")
        
        # Estimate expansion: if a customer has multiple closed won deals, 
        # the second+ deals are considered expansion
        for deal in new_arr_deals:
            previous_deals = Sales.objects.filter(
                company=company,
                client=deal.client,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__lt=deal.created_at,
            ).exists()
            
            if previous_deals:
                arr_value = deal.mrr * Decimal("12") if deal.mrr else Decimal("0.00")
                expansion_arr += arr_value

        # Calculate expansion rate (simplified)
        if new_arr_total > 0:
            expansion_rate = (expansion_arr / new_arr_total) * Decimal("100")

        # Calculate Churned ARR (closed lost deals)
        churned_deals = Sales.objects.filter(
            company=company,
            stage=SalesStageStatusChoices.CLOSED_LOST,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        
        churned_count = churned_deals.count()
        churned_arr = sum(
            (deal.mrr * Decimal("12") if deal.mrr else Decimal("0.00"))
            for deal in churned_deals
        )

        # Calculate Net New ARR
        net_new_arr = new_arr_total + expansion_arr - churned_arr

        response_data = {
            "new_arr": {
                "title": "New ARR (Period)",
                "value": float(new_arr_total),
                "value_display": self._format_amount_display(new_arr_total),
                "subtitle": f"{new_arr_count} deals closed",
            },
            "expansion_arr": {
                "title": "Expansion ARR (Est.)",
                "value": float(expansion_arr),
                "value_display": self._format_amount_display(expansion_arr),
                "subtitle": f"~{expansion_rate.quantize(Decimal('0.01'))}% expansion rate",
            },
            "churned_arr": {
                "title": "Churned ARR (Est.)",
                "value": float(churned_arr),
                "value_display": self._format_amount_display(churned_arr),
                "subtitle": f"{churned_count} deals lost",
            },
            "net_new_arr": {
                "title": "Net New ARR",
                "value": float(net_new_arr),
                "value_display": self._format_amount_display(net_new_arr),
                "subtitle": "Growth momentum",
            },
        }

        serializer = ARRSummarySerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

