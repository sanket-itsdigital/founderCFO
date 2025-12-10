from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.cohort_performance import CustomerCohortPerformanceSerializer
from sales.views.api.utils import get_company_from_request


class CustomerCohortPerformanceView(APIView):
    """
    Customer Cohort Performance API
    Returns retention, expansion, and churn percentages by quarter
    """

    permission_classes = [IsAuthenticated]

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
        else:  # quarter == 4
            start = datetime(year, 10, 1).date()
            end = datetime(year, 12, 31).date()
        return start, end

    def _calculate_cohort_metrics(self, company, start_date, end_date):
        """Calculate retention, expansion, and churn for a cohort period"""
        # Get all customers who had deals in the previous period
        previous_period_start = start_date - timedelta(days=90)  # Approximate previous quarter
        previous_period_end = start_date - timedelta(days=1)
        
        # Customers active in previous period
        previous_customers = set(
            Sales.objects.filter(
                company=company,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=previous_period_start,
                created_at__date__lte=previous_period_end,
            ).values_list("client", flat=True).distinct()
        )

        # Customers active in current period
        current_customers = set(
            Sales.objects.filter(
                company=company,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            ).values_list("client", flat=True).distinct()
        )

        # Calculate metrics
        if len(previous_customers) == 0:
            # If no previous customers, assume 100% retention for new customers
            retention_pct = Decimal("100.00")
            churn_pct = Decimal("0.00")
        else:
            # Retained customers (in both periods)
            retained_customers = previous_customers.intersection(current_customers)
            retention_pct = (Decimal(str(len(retained_customers))) / Decimal(str(len(previous_customers)))) * Decimal("100")
            
            # Churned customers (in previous but not current)
            churned_customers = previous_customers - current_customers
            churn_pct = (Decimal(str(len(churned_customers))) / Decimal(str(len(previous_customers)))) * Decimal("100")

        # Calculate expansion (customers with multiple deals or increased MRR)
        expansion_count = 0
        for customer in current_customers:
            customer_deals = Sales.objects.filter(
                company=company,
                client=customer,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            if customer_deals.count() > 1:
                expansion_count += 1
            else:
                # Check if MRR increased from previous period
                previous_deals = Sales.objects.filter(
                    company=company,
                    client=customer,
                    stage=SalesStageStatusChoices.CLOSED_WON,
                    created_at__date__gte=previous_period_start,
                    created_at__date__lte=previous_period_end,
                )
                if previous_deals.exists():
                    previous_mrr = sum(d.mrr for d in previous_deals if d.mrr) or Decimal("0.00")
                    current_mrr = sum(d.mrr for d in customer_deals if d.mrr) or Decimal("0.00")
                    if current_mrr > previous_mrr:
                        expansion_count += 1

        if len(current_customers) == 0:
            expansion_pct = Decimal("0.00")
        else:
            expansion_pct = (Decimal(str(expansion_count)) / Decimal(str(len(current_customers)))) * Decimal("100")

        return {
            "retention_percentage": float(retention_pct.quantize(Decimal("0.01"))),
            "expansion_percentage": float(expansion_pct.quantize(Decimal("0.01"))),
            "churn_percentage": float(churn_pct.quantize(Decimal("0.01"))),
        }

    def get(self, request):
        """Get Customer Cohort Performance data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get current year
        current_year = timezone.now().year
        
        # Calculate metrics for each quarter of the current year
        cohort_data = []
        for quarter in range(1, 5):
            start_date, end_date = self._get_quarter_dates(current_year, quarter)
            metrics = self._calculate_cohort_metrics(company, start_date, end_date)
            
            cohort_data.append({
                "period": f"Q{quarter} {current_year}",
                "retention_percentage": metrics["retention_percentage"],
                "expansion_percentage": metrics["expansion_percentage"],
                "churn_percentage": metrics["churn_percentage"],
            })

        response_data = {
            "title": "Customer Cohort Performance (Estimated)",
            "data": cohort_data,
        }

        serializer = CustomerCohortPerformanceSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

