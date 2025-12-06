from decimal import Decimal
from collections import defaultdict

from django.db.models import Q, Sum, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.pipeline_health import SalesPipelineHealthSerializer
from sales.views.api.utils import get_company_from_request


class SalesPipelineHealthView(APIView):
    """
    Sales Pipeline Health & Conversion API
    Returns pipeline data for each stage with opportunities, value, conversion rate, and health
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
            return SalesPipelineHealthView._in_crores(amount)
        else:
            return SalesPipelineHealthView._in_lakhs(amount)

    def _calculate_conversion_rate(self, stage_deals, next_stage_deals):
        """Calculate conversion rate from current stage to next stage"""
        if stage_deals == 0:
            return Decimal("0.00")
        if next_stage_deals == 0:
            return Decimal("0.00")
        return (Decimal(str(next_stage_deals)) / Decimal(str(stage_deals))) * Decimal("100")

    def get(self, request):
        """Get Sales Pipeline Health & Conversion data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get all available stages from the choices
        all_stages = [choice[0] for choice in SalesStageStatusChoices.choices]
        
        # Get all sales for the company
        all_sales = Sales.objects.filter(company=company)

        # Group by stage and calculate metrics
        stage_data = {}
        for stage in all_stages:
            stage_sales = all_sales.filter(stage=stage)
            opportunities = stage_sales.count()
            
            # Calculate pipeline value (amount * probability / 100)
            pipeline_value = sum(
                (deal.amount * (deal.probability / Decimal("100")))
                for deal in stage_sales
            )
            
            # Only include stages that have opportunities or pipeline value
            if opportunities > 0 or pipeline_value > 0:
                stage_data[stage] = {
                    "opportunities": opportunities,
                    "pipeline_value": pipeline_value,
                }

        # Calculate conversion rates and health for all stages
        pipeline_stages = []
        for stage, stage_info in stage_data.items():
            opportunities = stage_info["opportunities"]
            pipeline_value = stage_info["pipeline_value"]

            # Calculate conversion rate
            # For Closed Won, conversion rate is 100%
            if stage == SalesStageStatusChoices.CLOSED_WON:
                conversion_rate = Decimal("100.00")
            else:
                # For other stages, calculate based on deals that moved to next stage
                # This is a simplified calculation - in reality, you'd track stage transitions
                # For now, we'll use a default conversion rate based on stage position
                stage_index = all_stages.index(stage)
                if stage_index < len(all_stages) - 1:
                    next_stage = all_stages[stage_index + 1]
                    next_stage_opportunities = stage_data.get(next_stage, {}).get("opportunities", 0)
                    if opportunities > 0:
                        conversion_rate = (Decimal(str(next_stage_opportunities)) / Decimal(str(opportunities))) * Decimal("100")
                    else:
                        conversion_rate = Decimal("0.00")
                else:
                    conversion_rate = Decimal("0.00")

            # Health percentage is based on conversion rate
            health_percentage = min(conversion_rate, Decimal("100.00"))

            pipeline_stages.append({
                "stage": stage,
                "opportunities": opportunities,
                "pipeline_value": float(pipeline_value),
                "pipeline_value_display": self._format_amount_display(pipeline_value),
                "conversion_rate": float(conversion_rate),
                "conversion_rate_display": f"{conversion_rate.quantize(Decimal('0.01'))}%",
                "health_percentage": float(health_percentage),
            })

        # Sort by pipeline value (descending) and get top 5
        pipeline_stages.sort(key=lambda x: x["pipeline_value"], reverse=True)
        top_5_stages = pipeline_stages[:5]

        response_data = {
            "stages": top_5_stages,
        }

        serializer = SalesPipelineHealthSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

