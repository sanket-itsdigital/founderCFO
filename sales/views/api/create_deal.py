from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales, SalesTeam
from sales.enums import SalesStageStatusChoices
from sales.serializers.create_deal import CreateDealSerializer
from sales.views.api.utils import get_company_from_request


class CreateDealView(APIView):
    """
    Create Deal API
    Creates a new deal in the sales pipeline
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a new deal"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreateDealSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Get deal owner (sales team member)
        deal_owner = None
        if validated_data.get("deal_owner_id"):
            try:
                deal_owner = SalesTeam.objects.get(
                    id=validated_data["deal_owner_id"],
                    company=company,
                )
            except SalesTeam.DoesNotExist:
                return Response(
                    {"deal_owner_id": "Sales team member not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Generate unique deal_id
        deal_id = f"DEAL{uuid.uuid4().hex[:6].upper()}"

        # Calculate days in stage (default to 0 for new deals)
        days_in_stage = 0

        # Set default probability based on stage if not provided
        probability = validated_data.get("probability")
        if probability is None:
            stage = validated_data.get("stage", SalesStageStatusChoices.DISCOVERY)
            if stage == SalesStageStatusChoices.DISCOVERY:
                probability = Decimal("20.00")
            elif stage == SalesStageStatusChoices.QUALIFICATION:
                probability = Decimal("30.00")
            elif stage == SalesStageStatusChoices.PROPOSAL:
                probability = Decimal("50.00")
            elif stage == SalesStageStatusChoices.NEGOTIATION:
                probability = Decimal("70.00")
            elif stage == SalesStageStatusChoices.CLOSED_WON:
                probability = Decimal("100.00")
            else:
                probability = Decimal("20.00")
        else:
            probability = validated_data["probability"]

        # Create deal name from account name
        deal_name = f"{validated_data['account_name']} Deal"

        try:
            with transaction.atomic():
                deal = Sales.objects.create(
                    company=company,
                    deal_id=deal_id,
                    deal_name=deal_name,
                    client=validated_data["account_name"],
                    sales_team=deal_owner,
                    amount=validated_data["deal_amount"],
                    mrr=validated_data.get("monthly_recurring_revenue") or Decimal("0.00"),
                    stage=validated_data["stage"],
                    probability=probability,
                    close_date=validated_data["expected_close_date"],
                    subscription_product=validated_data.get("product"),
                    days_in_stage=days_in_stage,
                    last_activity=timezone.now().date(),
                    notes=validated_data.get("notes"),
                    created_by=request.user,
                    updated_by=request.user,
                )

                return Response(
                    {
                        "message": "Deal created successfully",
                        "deal_id": str(deal.id),
                        "deal": {
                            "id": str(deal.id),
                            "deal_id": deal.deal_id,
                            "deal_name": deal.deal_name,
                            "account_name": deal.client,
                            "owner": deal.sales_team.name if deal.sales_team else "Unassigned",
                            "product": deal.subscription_product or "",
                            "amount": float(deal.amount),
                            "mrr": float(deal.mrr),
                            "stage": deal.stage,
                            "probability": float(deal.probability),
                            "close_date": deal.close_date,
                            "status": "Open" if deal.stage not in [
                                SalesStageStatusChoices.CLOSED_WON,
                                SalesStageStatusChoices.CLOSED_LOST,
                            ] else ("Won" if deal.stage == SalesStageStatusChoices.CLOSED_WON else "Lost"),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return Response(
                {"error": f"Failed to create deal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

