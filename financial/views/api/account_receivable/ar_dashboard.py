from collections import defaultdict
from decimal import Decimal
from datetime import timedelta

from django.db.models import F, Sum, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from revenue.models.invoice import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.account_receivable.ar_dashboard import ARDashboardSerializer
from financial.views.api.account_receivable.ar_aging import get_company_from_request


class ARDashboardView(APIView):
    """
    Comprehensive AR Dashboard API that returns all key metrics:
    - Key Performance Indicators (KPIs)
    - AR Health Status
    - Ageing Distribution
    - Priority Actions
    - Top Customers by Revenue
    - Collection Trend
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

    def _calculate_dso(self, total_receivables, total_invoiced_last_90_days):
        """Calculate Days Sales Outstanding (DSO)"""
        if total_invoiced_last_90_days == 0:
            return 0
        # DSO = (Total Receivables / Total Sales) * Number of Days
        # Using 90 days as the period
        dso = (total_receivables / total_invoiced_last_90_days) * 90
        return int(dso)

    def _calculate_collection_efficiency(self, collected_amount, invoiced_amount):
        """Calculate Collection Efficiency percentage"""
        if invoiced_amount == 0:
            return 0.0
        efficiency = (collected_amount / invoiced_amount) * 100
        return round(float(efficiency), 1)

    def _calculate_avg_days_delinquent(self, overdue_invoices):
        """Calculate average days delinquent for overdue invoices"""
        if not overdue_invoices:
            return 0

        today = timezone.now().date()
        total_days = 0
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.due_date).days
            total_days += days_overdue

        return int(total_days / len(overdue_invoices))

    def _get_ar_health_status(self, overdue_percentage, dso, dso_target):
        """Determine overall AR health status"""
        if overdue_percentage >= 70 or dso > dso_target * 2:
            return "Critical"
        elif overdue_percentage >= 50 or dso > dso_target * 1.5:
            return "Needs Attention"
        else:
            return "Healthy"

    def _get_status_label(self, value, thresholds):
        """Get status label based on value and thresholds"""
        if value >= thresholds["high"]:
            return "High"
        elif value <= thresholds["low"]:
            return "Low"
        else:
            return "Normal"

    def _get_customer_concentration_status(self, percentage):
        """Get customer concentration status"""
        if percentage >= 30:
            return "High Risk"
        elif percentage >= 20:
            return "Concentrated"
        else:
            return "Diversified"

    def get(self, request, *args, **kwargs):
        """Calculate and return comprehensive AR dashboard data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        last_90_days_start = today - timedelta(days=90)
        week_start = today - timedelta(days=7)
        week_end = today + timedelta(days=7)

        # Get all invoices (excluding cancelled)
        all_invoices = Invoice.objects.filter(company=company).exclude(
            status=InvoicesStatusChoices.CANCELLED
        )

        # Get outstanding invoices
        outstanding_invoices = all_invoices.filter(
            total_amount__gt=F("paid_amount")
        ).exclude(status=InvoicesStatusChoices.PAID)

        # Calculate Total Receivables
        total_receivables = sum(
            invoice.balance_amount for invoice in outstanding_invoices
        )

        # Calculate Overdue AR
        overdue_invoices = [inv for inv in outstanding_invoices if inv.is_overdue]
        overdue_ar = sum(inv.balance_amount for inv in overdue_invoices)
        overdue_percentage = (
            (overdue_ar / total_receivables * 100) if total_receivables > 0 else 0.0
        )

        # Calculate DSO
        # Total invoiced in last 90 days
        invoiced_last_90_days = all_invoices.filter(
            invoice_date__gte=last_90_days_start
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        dso = self._calculate_dso(total_receivables, invoiced_last_90_days)
        dso_target = 30  # Standard target

        # Calculate Collection Efficiency (last 90 days)
        collected_last_90_days = all_invoices.filter(
            invoice_date__gte=last_90_days_start
        ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0.00")
        collection_efficiency = self._calculate_collection_efficiency(
            collected_last_90_days, invoiced_last_90_days
        )

        # Calculate Average Days Delinquent
        avg_days_delinquent = self._calculate_avg_days_delinquent(overdue_invoices)

        # This Month Collections
        this_month_collections = all_invoices.filter(
            status=InvoicesStatusChoices.PAID, updated_at__gte=current_month_start
        ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0.00")

        # Invoice Status Counts
        invoice_status_counts = {
            "total": all_invoices.count(),
            "paid": all_invoices.filter(status=InvoicesStatusChoices.PAID).count(),
            "pending": all_invoices.filter(
                status=InvoicesStatusChoices.PENDING
            ).count(),
            "overdue": all_invoices.filter(
                status=InvoicesStatusChoices.OVERDUE
            ).count(),
        }

        # Ageing Distribution
        ageing_buckets = {
            "current": Decimal("0"),
            "1_30_days": Decimal("0"),
            "31_60_days": Decimal("0"),
            "61_90_days": Decimal("0"),
            "90_plus_days": Decimal("0"),
        }

        for invoice in outstanding_invoices:
            days_until_due = (invoice.due_date - today).days
            balance = invoice.balance_amount

            if days_until_due == 0:
                ageing_buckets["current"] += balance
            elif days_until_due > 0 and days_until_due <= 30:
                ageing_buckets["1_30_days"] += balance
            elif days_until_due > 30 and days_until_due <= 60:
                ageing_buckets["31_60_days"] += balance
            elif days_until_due > 60 and days_until_due <= 90:
                ageing_buckets["61_90_days"] += balance
            else:
                ageing_buckets["90_plus_days"] += balance

        ageing_distribution = [
            {
                "label": "Current",
                "amount": float(ageing_buckets["current"]),
                "amount_display": self._in_lakhs(ageing_buckets["current"]),
                "percentage": (
                    float((ageing_buckets["current"] / total_receivables * 100))
                    if total_receivables > 0
                    else 0.0
                ),
                "color": "green",
            },
            {
                "label": "1-30 Days",
                "amount": float(ageing_buckets["1_30_days"]),
                "amount_display": self._in_lakhs(ageing_buckets["1_30_days"]),
                "percentage": (
                    float((ageing_buckets["1_30_days"] / total_receivables * 100))
                    if total_receivables > 0
                    else 0.0
                ),
                "color": "blue",
            },
            {
                "label": "31-60 Days",
                "amount": float(ageing_buckets["31_60_days"]),
                "amount_display": self._in_lakhs(ageing_buckets["31_60_days"]),
                "percentage": (
                    float((ageing_buckets["31_60_days"] / total_receivables * 100))
                    if total_receivables > 0
                    else 0.0
                ),
                "color": "orange",
            },
            {
                "label": "61-90 Days",
                "amount": float(ageing_buckets["61_90_days"]),
                "amount_display": self._in_lakhs(ageing_buckets["61_90_days"]),
                "percentage": (
                    float((ageing_buckets["61_90_days"] / total_receivables * 100))
                    if total_receivables > 0
                    else 0.0
                ),
                "color": "red",
            },
            {
                "label": "90+ Days",
                "amount": float(ageing_buckets["90_plus_days"]),
                "amount_display": self._in_lakhs(ageing_buckets["90_plus_days"]),
                "percentage": (
                    float((ageing_buckets["90_plus_days"] / total_receivables * 100))
                    if total_receivables > 0
                    else 0.0
                ),
                "color": "dark_red",
            },
        ]

        # Priority Actions
        critical_count = len(
            [inv for inv in overdue_invoices if (today - inv.due_date).days > 90]
        )
        due_this_week = outstanding_invoices.filter(
            due_date__gte=week_start, due_date__lte=week_end
        ).count()

        # Top 5 Customers by Revenue
        customer_outstanding = defaultdict(
            lambda: {"outstanding": Decimal("0"), "invoices": []}
        )
        for invoice in outstanding_invoices:
            customer_outstanding[invoice.customer_name][
                "outstanding"
            ] += invoice.balance_amount
            customer_outstanding[invoice.customer_name]["invoices"].append(invoice)

        top_customers = sorted(
            [
                {
                    "customer_name": name,
                    "invoice_count": len(data["invoices"]),
                    "outstanding": float(data["outstanding"]),
                    "outstanding_display": self._in_lakhs(data["outstanding"]),
                    "percentage": (
                        float((data["outstanding"] / total_receivables * 100))
                        if total_receivables > 0
                        else 0.0
                    ),
                }
                for name, data in customer_outstanding.items()
            ],
            key=lambda x: x["outstanding"],
            reverse=True,
        )[:5]

        # Top Customer Concentration
        top_customer_concentration = (
            top_customers[0]["percentage"] if top_customers else 0.0
        )
        top_customer_name = (
            top_customers[0]["customer_name"] if top_customers else "N/A"
        )

        # Collection Trend (Last 6 months)
        collection_trend = []
        for i in range(5, -1, -1):  # Last 6 months
            month_start = (current_month_start - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(
                days=1
            )

            month_invoiced = all_invoices.filter(
                invoice_date__gte=month_start, invoice_date__lte=month_end
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

            month_collected = all_invoices.filter(
                status=InvoicesStatusChoices.PAID,
                updated_at__gte=month_start,
                updated_at__lte=month_end,
            ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0.00")

            month_name = month_start.strftime("%b")
            collection_trend.append(
                {
                    "month": month_name,
                    "collected": float(month_collected),
                    "collected_display": self._in_lakhs(month_collected),
                    "invoiced": float(month_invoiced),
                    "invoiced_display": self._in_lakhs(month_invoiced),
                }
            )

        # Build response
        response_data = {
            "kpis": {
                "total_receivables": float(total_receivables),
                "total_receivables_display": self._in_crores(total_receivables),
                "total_receivables_trend": None,  # Can be calculated from previous period
                "dso": dso,
                "collection_efficiency": collection_efficiency,
                "overdue_ar": float(overdue_ar),
                "overdue_ar_percentage": round(overdue_percentage, 1),
                "overdue_ar_display": self._in_crores(overdue_ar),
                "avg_days_delinquent": avg_days_delinquent,
                "this_month_collections": float(this_month_collections),
                "this_month_collections_display": self._in_lakhs(
                    this_month_collections
                ),
                "this_month_collections_trend": None,  # Can be calculated from previous month
                "invoice_status": invoice_status_counts,
            },
            "ar_health_status": {
                "status": self._get_ar_health_status(
                    overdue_percentage, dso, dso_target
                ),
                "total_receivables": float(total_receivables),
                "total_receivables_display": self._in_crores(total_receivables),
                "metrics": {
                    "dso": dso,
                    "dso_target": dso_target,
                    "dso_status": self._get_status_label(
                        dso, {"high": dso_target * 1.5, "low": dso_target * 0.8}
                    ),
                    "collection_efficiency": collection_efficiency,
                    "collection_efficiency_status": self._get_status_label(
                        collection_efficiency, {"high": 80, "low": 50}
                    ),
                    "overdue_amount": float(overdue_ar),
                    "overdue_amount_display": self._in_crores(overdue_ar),
                    "overdue_percentage": round(overdue_percentage, 1),
                    "top_customer_concentration": round(top_customer_concentration, 1),
                    "top_customer_name": top_customer_name,
                    "top_customer_status": self._get_customer_concentration_status(
                        top_customer_concentration
                    ),
                },
            },
            "ageing_distribution": ageing_distribution,
            "priority_actions": {
                "critical_count": critical_count,
                "due_this_week_count": due_this_week,
                "collected_this_month": float(this_month_collections),
                "collected_this_month_display": self._in_lakhs(this_month_collections),
            },
            "top_customers": top_customers,
            "collection_trend": collection_trend,
        }

        # Validate with serializer
        serializer = ARDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
