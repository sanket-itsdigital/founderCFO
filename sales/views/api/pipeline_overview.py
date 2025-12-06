from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.pipeline_overview import PipelineOverviewSerializer
from sales.views.api.utils import get_company_from_request


class PipelineOverviewView(APIView):
    """
    Pipeline Overview API
    Returns list of all deals in pipeline table format
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount with commas"""
        return f"₹{amount:,.0f}"

    def get(self, request):
        """Get Pipeline Overview data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get query parameters for filtering
        stage_filter = request.query_params.get("stage", None)
        search_query = request.query_params.get("search", None)
        
        # Get all deals
        deals = Sales.objects.filter(company=company).select_related("sales_team").order_by("-created_at")

        # Apply stage filter
        if stage_filter and stage_filter != "All Stages":
            deals = deals.filter(stage=stage_filter)

        # Apply search filter
        if search_query:
            deals = deals.filter(
                Q(deal_name__icontains=search_query) |
                Q(client__icontains=search_query) |
                Q(deal_id__icontains=search_query) |
                Q(sales_team__name__icontains=search_query)
            )

        deals_data = []
        for deal in deals:
            # Determine status based on stage
            if deal.stage == SalesStageStatusChoices.CLOSED_WON:
                deal_status = "Won"
            elif deal.stage == SalesStageStatusChoices.CLOSED_LOST:
                deal_status = "Lost"
            else:
                deal_status = "Open"

            deals_data.append({
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
                "close_date_display": deal.close_date.strftime("%d %b %Y") if deal.close_date else "",
                "status": deal_status,
            })

        response_data = {
            "title": "Pipeline Overview",
            "deals": deals_data,
            "total_count": len(deals_data),
        }

        serializer = PipelineOverviewSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

