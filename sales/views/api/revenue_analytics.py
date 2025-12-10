from collections import defaultdict
from decimal import Decimal
from datetime import timedelta, datetime
from calendar import month_abbr

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices
from sales.serializers.revenue_analytics import RevenueAnalyticsSerializer
from sales.views.api.utils import get_company_from_request


class RevenueAnalyticsView(APIView):
    """
    Combined Revenue Analytics API
    Returns all revenue-related analytics in one response:
    - ARR Summary
    - Cohort Performance
    - Sales Performance (with ARR Waterfall)
    - Pipeline Health
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
            return RevenueAnalyticsView._in_crores(amount)
        else:
            return RevenueAnalyticsView._in_lakhs(amount)

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

    def _calculate_arr_waterfall(self, company, start_date, end_date):
        """Calculate ARR Growth Waterfall by month"""
        sales = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).order_by("created_at")

        monthly_data = defaultdict(lambda: {
            "new_revenue": Decimal("0.00"),
            "expansion": Decimal("0.00"),
            "churn": Decimal("0.00"),
        })

        for sale in sales:
            year_month = sale.created_at.strftime("%Y-%m")
            arr_value = sale.mrr * Decimal("12") if sale.mrr else Decimal("0.00")
            
            if sale.stage == SalesStageStatusChoices.CLOSED_WON:
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
                monthly_data[year_month]["churn"] += arr_value

        waterfall_data = []
        running_total_arr = Decimal("0.00")
        sorted_months = sorted(monthly_data.keys())
        
        for year_month in sorted_months:
            try:
                month_num = int(year_month.split("-")[1])
                month_name = month_abbr[month_num]
            except (IndexError, ValueError, KeyError):
                month_name = year_month
            
            new_rev = monthly_data[year_month]["new_revenue"]
            expansion = monthly_data[year_month]["expansion"]
            churn = monthly_data[year_month]["churn"]
            
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

    def _calculate_arr_summary(self, company, start_date, end_date):
        """Calculate ARR Summary"""
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

        expansion_arr = Decimal("0.00")
        expansion_rate = Decimal("0.00")
        
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

        if new_arr_total > 0:
            expansion_rate = (expansion_arr / new_arr_total) * Decimal("100")

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

        net_new_arr = new_arr_total + expansion_arr - churned_arr

        return {
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

    def _calculate_cohort_performance(self, company):
        """Calculate Customer Cohort Performance"""
        current_year = timezone.now().year
        cohort_data = []
        
        for quarter in range(1, 5):
            start_date, end_date = self._get_quarter_dates(current_year, quarter)
            previous_period_start = start_date - timedelta(days=90)
            previous_period_end = start_date - timedelta(days=1)
            
            previous_customers = set(
                Sales.objects.filter(
                    company=company,
                    stage=SalesStageStatusChoices.CLOSED_WON,
                    created_at__date__gte=previous_period_start,
                    created_at__date__lte=previous_period_end,
                ).values_list("client", flat=True).distinct()
            )

            current_customers = set(
                Sales.objects.filter(
                    company=company,
                    stage=SalesStageStatusChoices.CLOSED_WON,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                ).values_list("client", flat=True).distinct()
            )

            if len(previous_customers) == 0:
                retention_pct = Decimal("100.00")
                churn_pct = Decimal("0.00")
            else:
                retained_customers = previous_customers.intersection(current_customers)
                retention_pct = (Decimal(str(len(retained_customers))) / Decimal(str(len(previous_customers)))) * Decimal("100")
                churned_customers = previous_customers - current_customers
                churn_pct = (Decimal(str(len(churned_customers))) / Decimal(str(len(previous_customers)))) * Decimal("100")

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

            cohort_data.append({
                "period": f"Q{quarter} {current_year}",
                "retention_percentage": float(retention_pct.quantize(Decimal("0.01"))),
                "expansion_percentage": float(expansion_pct.quantize(Decimal("0.01"))),
                "churn_percentage": float(churn_pct.quantize(Decimal("0.01"))),
            })

        return {
            "title": "Customer Cohort Performance (Estimated)",
            "data": cohort_data,
        }

    def _calculate_pipeline_health(self, company):
        """Calculate Sales Pipeline Health"""
        all_stages = [choice[0] for choice in SalesStageStatusChoices.choices]
        all_sales = Sales.objects.filter(company=company)

        stage_data = {}
        for stage in all_stages:
            stage_sales = all_sales.filter(stage=stage)
            opportunities = stage_sales.count()
            pipeline_value = sum(
                (deal.amount * (deal.probability / Decimal("100")))
                for deal in stage_sales
            )
            
            if opportunities > 0 or pipeline_value > 0:
                stage_data[stage] = {
                    "opportunities": opportunities,
                    "pipeline_value": pipeline_value,
                }

        pipeline_stages = []
        for stage, stage_info in stage_data.items():
            opportunities = stage_info["opportunities"]
            pipeline_value = stage_info["pipeline_value"]

            if stage == SalesStageStatusChoices.CLOSED_WON:
                conversion_rate = Decimal("100.00")
            else:
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

        pipeline_stages.sort(key=lambda x: x["pipeline_value"], reverse=True)
        top_5_stages = pipeline_stages[:5]

        return {"stages": top_5_stages}

    def _calculate_sales_performance(self, company, start_date, end_date):
        """Calculate Sales Performance Summary"""
        total_deals = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).count()

        unique_reps = Sales.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            sales_team__isnull=False,
        ).values("sales_team").distinct().count()

        activities = Sales.objects.filter(
            company=company,
            last_activity__gte=start_date,
            last_activity__lte=end_date,
        ).count()

        arr_waterfall_data = self._calculate_arr_waterfall(company, start_date, end_date)

        return {
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

    def get(self, request):
        """Get combined Revenue Analytics data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        # Calculate all metrics
        arr_summary = self._calculate_arr_summary(company, start_date, end_date)
        cohort_performance = self._calculate_cohort_performance(company)
        pipeline_health = self._calculate_pipeline_health(company)
        sales_performance = self._calculate_sales_performance(company, start_date, end_date)

        response_data = {
            "arr_summary": arr_summary,
            "cohort_performance": cohort_performance,
            "pipeline_health": pipeline_health,
            "sales_performance": sales_performance,
        }

        serializer = RevenueAnalyticsSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

