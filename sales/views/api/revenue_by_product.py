from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.models import Sales
from sales.enums import SalesStageStatusChoices, SalesProductChoices
from sales.serializers.revenue_by_product import RevenueByProductSerializer
from sales.views.api.utils import get_company_from_request


class RevenueByProductView(APIView):
    """
    Revenue by Product Line API
    Returns revenue breakdown by product (Enterprise, Pro, Starter)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _in_crores(amount: Decimal) -> str:
        """Convert amount to crores format (₹XX.XXCr)"""
        if amount == 0:
            return "₹0.00Cr"
        crores = amount / Decimal("10000000")
        return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as L or Cr based on value"""
        if amount >= Decimal("10000000"):
            return RevenueByProductView._in_crores(amount)
        else:
            return RevenueByProductView._in_lakhs(amount)

    def _get_date_range(self, period):
        """Get date range based on period filter"""
        today = timezone.now().date()

        if period == "7":
            start_date = today - timedelta(days=7)
        elif period == "30":
            start_date = today - timedelta(days=30)
        elif period == "90":
            start_date = today - timedelta(days=90)
        elif period == "365" or period == "year":
            start_date = today - timedelta(days=365)
        elif period == "quarter":
            # Current quarter
            current_month = today.month
            if current_month <= 3:
                start_date = datetime(today.year, 1, 1).date()
            elif current_month <= 6:
                start_date = datetime(today.year, 4, 1).date()
            elif current_month <= 9:
                start_date = datetime(today.year, 7, 1).date()
            else:
                start_date = datetime(today.year, 10, 1).date()
        else:
            # Default to 30 days
            start_date = today - timedelta(days=30)

        return start_date, today

    def _calculate_yoy_growth(
        self, company, product, current_revenue, start_date, end_date
    ):
        """Calculate Year-over-Year growth for a product"""
        # Get same period last year
        last_year_start = datetime(
            start_date.year - 1, start_date.month, start_date.day
        ).date()
        last_year_end = datetime(end_date.year - 1, end_date.month, end_date.day).date()

        last_year_sales = Sales.objects.filter(
            company=company,
            subscription_product=product,
            stage=SalesStageStatusChoices.CLOSED_WON,
            created_at__date__gte=last_year_start,
            created_at__date__lte=last_year_end,
        )
        last_year_revenue = sum(deal.amount for deal in last_year_sales) or Decimal(
            "0.00"
        )

        if last_year_revenue == 0:
            return None

        growth = ((current_revenue - last_year_revenue) / last_year_revenue) * Decimal(
            "100"
        )
        return growth.quantize(Decimal("0"))

    def get(self, request):
        """Get Revenue by Product Line data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get period filter (default to 30 days)
        period = request.query_params.get("period", "30")
        start_date, end_date = self._get_date_range(period)

        product_lines_data = []
        total_revenue = Decimal("0.00")
        total_deals = 0
        total_deal_amount = Decimal("0.00")

        # Process each product
        for product_choice in SalesProductChoices.choices:
            product = product_choice[0]

            # Get closed won deals for this product
            product_sales = Sales.objects.filter(
                company=company,
                subscription_product=product,
                stage=SalesStageStatusChoices.CLOSED_WON,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )

            revenue = sum(deal.amount for deal in product_sales) or Decimal("0.00")
            deals_closed = product_sales.count()
            avg_deal_size = (
                (revenue / deals_closed) if deals_closed > 0 else Decimal("0.00")
            )

            # Calculate YoY growth
            yoy_growth = self._calculate_yoy_growth(
                company, product, revenue, start_date, end_date
            )

            product_lines_data.append(
                {
                    "product": product,
                    "revenue": float(revenue),
                    "revenue_display": self._format_amount_display(revenue),
                    "deals_closed": deals_closed,
                    "avg_deal_size": float(avg_deal_size),
                    "avg_deal_size_display": self._format_amount_display(avg_deal_size),
                    "yoy_growth": float(yoy_growth) if yoy_growth is not None else None,
                    "yoy_growth_display": (
                        f"+{yoy_growth}%"
                        if yoy_growth is not None and yoy_growth > 0
                        else f"{yoy_growth}%" if yoy_growth is not None else None
                    ),
                }
            )

            total_revenue += revenue
            total_deals += deals_closed
            total_deal_amount += revenue

        # Calculate total average deal size
        total_avg_deal_size = (
            (total_deal_amount / total_deals) if total_deals > 0 else Decimal("0.00")
        )

        # Total row
        total_row = {
            "product": "Total",
            "revenue": float(total_revenue),
            "revenue_display": self._format_amount_display(total_revenue),
            "deals_closed": total_deals,
            "avg_deal_size": float(total_avg_deal_size),
            "avg_deal_size_display": self._format_amount_display(total_avg_deal_size),
            "yoy_growth": None,
            "yoy_growth_display": None,
        }

        response_data = {
            "title": "Revenue by Product Line",
            "subtitle": f"Revenue breakdown for {period} days period",
            "product_lines": product_lines_data,
            "total": total_row,
        }

        serializer = RevenueByProductSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
