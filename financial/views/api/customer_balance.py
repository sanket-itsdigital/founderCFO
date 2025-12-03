from collections import defaultdict
from decimal import Decimal

from django.db.models import F, Count, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.models.credit import Credit
from financial.enums import InvoicesStatusChoices
from financial.serializers.customer_balance import CustomerBalanceSummarySerializer
from financial.views.api.ar_aging import get_company_from_request


class CustomerBalanceSummaryView(APIView):
    """
    API view to get Customer Balance Summary.

    Returns:
    - Total customers count
    - List of customers with:
      - Outstanding amount
      - Credit limit (default 5 lakh, editable per customer)
      - Utilization percentage
      - Number of invoices
      - Average days outstanding (based on invoice_date)
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

    def get(self, request, *args, **kwargs):
        """Calculate and return customer balance summary"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "total_customers": 0,
                    "customers": [],
                    "summary": {
                        "total_outstanding": 0,
                        "total_outstanding_display": "₹0.00Cr",
                        "high_utilization": 0,
                        "slow_payers": 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()
        default_credit_limit = Decimal("500000.00")  # 5 lakh default

        # Get all outstanding invoices (not paid or cancelled)
        invoices = (
            Invoice.objects.filter(company=company)
            .exclude(
                status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
            )
            .filter(total_amount__gt=F("paid_amount"))
        )

        # Group invoices by customer
        customer_data = defaultdict(
            lambda: {
                "outstanding": Decimal("0"),
                "invoices": [],
                "invoice_dates": [],
            }
        )

        for invoice in invoices:
            customer_name = invoice.customer_name
            balance = invoice.balance_amount
            customer_data[customer_name]["outstanding"] += balance
            customer_data[customer_name]["invoices"].append(invoice)
            customer_data[customer_name]["invoice_dates"].append(invoice.invoice_date)

        # Get or create Credit records for all customers
        customers_list = []
        for customer_name, data in customer_data.items():
            # Get or create credit record with default 5 lakh limit
            credit, created = Credit.objects.get_or_create(
                company=company,
                customer_name=customer_name,
                defaults={
                    "credit_limit": default_credit_limit,
                    "created_by": (
                        request.user if request.user.is_authenticated else None
                    ),
                    "updated_by": (
                        request.user if request.user.is_authenticated else None
                    ),
                },
            )

            # Calculate average days outstanding based on invoice_date
            # Uses the maximum days (oldest invoice) - days from the oldest invoice_date to today
            avg_days = 0
            if data["invoices"]:
                max_days = 0
                for invoice in data["invoices"]:
                    days_since_invoice = (today - invoice.invoice_date).days
                    if days_since_invoice > max_days:
                        max_days = days_since_invoice
                avg_days = max_days

            # Calculate utilization percentage
            utilization = 0.0
            if credit.credit_limit > 0:
                utilization = float((data["outstanding"] / credit.credit_limit) * 100)

            customers_list.append(
                {
                    "customer_name": customer_name,
                    "outstanding": float(data["outstanding"]),
                    "outstanding_display": self._in_lakhs(data["outstanding"]),
                    "credit_limit": float(credit.credit_limit),
                    "credit_limit_display": self._in_lakhs(credit.credit_limit),
                    "utilization": round(utilization, 1),
                    "invoices": len(data["invoices"]),
                    "avg_days": avg_days,
                }
            )

        # Sort by outstanding amount (descending)
        customers_list.sort(key=lambda x: x["outstanding"], reverse=True)

        # Calculate summary statistics
        total_outstanding = sum(
            Decimal(str(customer["outstanding"])) for customer in customers_list
        )
        high_utilization_count = sum(
            1 for customer in customers_list if customer["utilization"] >= 100
        )
        slow_payers_count = sum(
            1 for customer in customers_list if customer["avg_days"] >= 45
        )

        response_data = {
            "total_customers": len(customers_list),
            "customers": customers_list,
            "summary": {
                "total_outstanding": float(total_outstanding),
                "total_outstanding_display": self._in_crores(total_outstanding),
                "high_utilization": high_utilization_count,
                "slow_payers": slow_payers_count,
            },
        }

        # Validate with serializer
        serializer = CustomerBalanceSummarySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
