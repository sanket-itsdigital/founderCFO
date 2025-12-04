from decimal import Decimal
from datetime import timedelta
from collections import defaultdict
from calendar import monthrange

from django.db.models import Sum, F, Count, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.models.reconcile import BankTransaction
from financial.enums import InvoicesStatusChoices, InvoicesCategoryChoices
from financial.serializers.account_receivable.analytics import (
    InvoicedCollectedTrendSerializer,
    DSOTrendSerializer,
    OutstandingByCategorySerializer,
    TopOutstandingSerializer,
    CollectionsByPaymentMethodSerializer,
    MonthlyCollectionRateSerializer,
)
from financial.views.api.account_receivable.ar_aging import get_company_from_request


class AnalyticsView(APIView):
    """Get all analytics data for reports"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "invoiced_collected_trend": [],
                "dso_trend": [],
                "outstanding_by_category": [],
                "top_outstanding": [],
                "collections_by_payment_method": [],
                "monthly_collection_rate": [],
            })

        today = timezone.now().date()
        
        # Get all invoices
        all_invoices = Invoice.objects.filter(company=company)
        paid_invoices = all_invoices.filter(status=InvoicesStatusChoices.PAID)
        outstanding_invoices = all_invoices.exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(total_amount__gt=F('paid_amount'))

        # 1. Invoiced vs Collected Trend (Last 6 months)
        invoiced_collected_trend = self._calculate_invoiced_collected_trend(
            company, all_invoices, paid_invoices
        )

        # 2. DSO Trend
        dso_trend = self._calculate_dso_trend(company, outstanding_invoices, today)

        # 3. Outstanding by Category
        outstanding_by_category = self._calculate_outstanding_by_category(outstanding_invoices)

        # 4. Top 5 Outstanding
        top_outstanding = self._calculate_top_outstanding(outstanding_invoices)

        # 5. Collections by Payment Method
        collections_by_payment_method = self._calculate_collections_by_payment_method(company)

        # 6. Monthly Collection Rate
        monthly_collection_rate = self._calculate_monthly_collection_rate(
            company, all_invoices, paid_invoices
        )

        return Response({
            "invoiced_collected_trend": invoiced_collected_trend,
            "dso_trend": dso_trend,
            "outstanding_by_category": outstanding_by_category,
            "top_outstanding": top_outstanding,
            "collections_by_payment_method": collections_by_payment_method,
            "monthly_collection_rate": monthly_collection_rate,
        })

    def _calculate_invoiced_collected_trend(self, company, all_invoices, paid_invoices):
        """Calculate invoiced vs collected trend for last 6 months"""
        today = timezone.now().date()
        trend_data = []
        
        for i in range(5, -1, -1):  # Last 6 months
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            
            # Get last day of month
            last_day = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)
            
            # Invoiced amount (total invoices created in this month)
            invoiced = all_invoices.filter(
                invoice_date__gte=month_start,
                invoice_date__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal("0.00")
            
            # Collected amount (payments received in this month)
            collected = paid_invoices.filter(
                updated_at__date__gte=month_start,
                updated_at__date__lte=month_end
            ).aggregate(total=Sum('paid_amount'))['total'] or Decimal("0.00")
            
            trend_data.append({
                "month": month_start.strftime("%b"),
                "invoiced": float(invoiced),
                "invoiced_display": self._in_lakhs(invoiced),
                "collected": float(collected),
                "collected_display": self._in_lakhs(collected),
            })
        
        return trend_data

    def _calculate_dso_trend(self, company, outstanding_invoices, today):
        """Calculate DSO (Days Sales Outstanding) trend"""
        dso_data = []
        current_dso = 0
        
        for i in range(5, -1, -1):  # Last 6 months
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            
            last_day = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)
            
            # Calculate DSO for this month
            # DSO = (Accounts Receivable / Total Credit Sales) * Number of Days
            ar = outstanding_invoices.filter(
                due_date__lte=month_end
            ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal("0.00")
            
            # Get credit sales for the month (invoices created)
            credit_sales = Invoice.objects.filter(
                company=company,
                invoice_date__gte=month_start,
                invoice_date__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal("0.00")
            
            if credit_sales > 0:
                days_in_month = (month_end - month_start).days + 1
                dso = float((ar / credit_sales) * days_in_month)
            else:
                dso = 0
            
            if i == 0:  # Current month
                current_dso = int(dso)
            
            dso_data.append({
                "month": month_start.strftime("%b"),
                "dso": int(dso),
            })
        
        # Add current_dso to all entries
        for entry in dso_data:
            entry["current_dso"] = current_dso
        
        return dso_data

    def _calculate_outstanding_by_category(self, outstanding_invoices):
        """Calculate outstanding amounts by category"""
        category_totals = defaultdict(Decimal)
        category_colors = {
            "Services": "#8B5CF6",  # Purple
            "Consulting": "#10B981",  # Green
            "Products Sales": "#EC4899",  # Pink
            "Maintenance": "#F97316",  # Orange
            "Subscriptions": "#3B82F6",  # Blue
            "Other": "#6B7280",  # Grey
        }
        
        for invoice in outstanding_invoices:
            category = invoice.category or "Other"
            balance = invoice.balance_amount
            category_totals[category] += balance
        
        result = []
        for category, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            result.append({
                "category": category,
                "amount": float(amount),
                "amount_display": self._in_lakhs(amount),
                "color": category_colors.get(category, "#6B7280"),
            })
        
        return result

    def _calculate_top_outstanding(self, outstanding_invoices):
        """Calculate top 5 outstanding customers"""
        customer_totals = defaultdict(Decimal)
        
        for invoice in outstanding_invoices:
            customer_totals[invoice.customer_name] += invoice.balance_amount
        
        top_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = []
        for customer_name, amount in top_customers:
            result.append({
                "customer_name": customer_name,
                "outstanding": float(amount),
                "outstanding_display": self._in_lakhs(amount),
            })
        
        return result

    def _calculate_collections_by_payment_method(self, company):
        """Calculate collections by payment method"""
        # Get matched bank transactions (these represent collections)
        matched_transactions = BankTransaction.objects.filter(
            company=company,
            is_matched=True
        )
        
        method_totals = defaultdict(Decimal)
        method_colors = {
            "Cheque": "#3B82F6",  # Blue
            "UPI": "#8B5CF6",  # Purple
            "Bank Transfer": "#F97316",  # Orange
            "Card": "#10B981",  # Green
            "Cash": "#6B7280",  # Grey
            "NEFT": "#3B82F6",
            "RTGS": "#3B82F6",
            "IMPS": "#3B82F6",
        }
        
        for transaction in matched_transactions:
            method = transaction.get_transaction_type_display()
            # Group NEFT, RTGS, IMPS as "Bank Transfer"
            if method in ["NEFT", "RTGS", "IMPS"]:
                method = "Bank Transfer"
            method_totals[method] += transaction.amount
        
        result = []
        for method, amount in sorted(method_totals.items(), key=lambda x: x[1], reverse=True):
            result.append({
                "payment_method": method,
                "amount": float(amount),
                "amount_display": self._in_lakhs(amount),
                "color": method_colors.get(method, "#6B7280"),
            })
        
        return result

    def _calculate_monthly_collection_rate(self, company, all_invoices, paid_invoices):
        """Calculate monthly collection rate"""
        today = timezone.now().date()
        rate_data = []
        
        for i in range(5, -1, -1):  # Last 6 months
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            
            last_day = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)
            
            # Invoiced in this month
            invoiced = all_invoices.filter(
                invoice_date__gte=month_start,
                invoice_date__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal("0.00")
            
            # Collected in this month
            collected = paid_invoices.filter(
                updated_at__date__gte=month_start,
                updated_at__date__lte=month_end
            ).aggregate(total=Sum('paid_amount'))['total'] or Decimal("0.00")
            
            # Collection rate
            if invoiced > 0:
                rate = float((collected / invoiced) * 100)
            else:
                rate = 0.0
            
            rate_data.append({
                "month": month_start.strftime("%b"),
                "collection_rate": round(rate, 1),
                "collection_rate_display": f"{round(rate, 1)}%",
            })
        
        return rate_data

