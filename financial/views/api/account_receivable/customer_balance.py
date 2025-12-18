from collections import defaultdict
from decimal import Decimal

from django.db.models import F, Count, Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from revenue.models.invoice import Invoice
from financial.models.account_receivable.credit import Credit
from financial.models.account_receivable.reconcile import BankTransaction
from financial.enums import InvoicesStatusChoices, RiskLevelChoices
from financial.serializers.account_receivable.customer_balance import (
    CustomerBalanceSummarySerializer,
    CustomerBalanceDetailSerializer,
    CustomerBalanceUpdateSerializer,
)
from financial.views.api.account_receivable.ar_aging import get_company_from_request


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
        invoices = Invoice.objects.filter(company=company).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
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
            # Calculate paid amount from matched transactions
            paid_amount = invoice.matched_transactions.aggregate(total=Sum("amount"))[
                "total"
            ] or Decimal("0.00")

            # Calculate balance (outstanding amount)
            balance = invoice.total_amount - paid_amount

            # Only include invoices with outstanding balance
            if balance > 0:
                customer_name = invoice.customer_name
                customer_data[customer_name]["outstanding"] += balance
                customer_data[customer_name]["invoices"].append(invoice)
                customer_data[customer_name]["invoice_dates"].append(
                    invoice.invoice_date
                )

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


class CustomerBalanceDetailView(APIView):
    """
    API view for individual customer balance operations.
    GET: Retrieve customer balance details
    PUT/PATCH: Update customer credit information
    DELETE: Delete customer credit record
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _get_customer_balance_data(self, company, customer_name):
        """Calculate customer balance data from invoices"""
        today = timezone.now().date()

        # Get all outstanding invoices for this customer
        invoices = Invoice.objects.filter(
            company=company, customer_name=customer_name
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        )

        # Calculate outstanding amount from invoices with balance > 0
        outstanding = Decimal("0.00")
        for invoice in invoices:
            # Calculate paid amount from matched transactions
            paid_amount = invoice.matched_transactions.aggregate(total=Sum("amount"))[
                "total"
            ] or Decimal("0.00")
            balance = invoice.total_amount - paid_amount
            if balance > 0:
                outstanding += balance

        # Calculate average days outstanding
        avg_days = 0
        if invoices:
            max_days = 0
            for invoice in invoices:
                days_since_invoice = (today - invoice.invoice_date).days
                if days_since_invoice > max_days:
                    max_days = days_since_invoice
            avg_days = max_days

        return outstanding, len(invoices), avg_days

    def get(self, request, customer_name, *args, **kwargs):
        """Get individual customer balance details"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get or create credit record
        try:
            credit = Credit.objects.get(company=company, customer_name=customer_name)
        except Credit.DoesNotExist:
            # Create default credit record
            credit = Credit.objects.create(
                company=company,
                customer_name=customer_name,
                credit_limit=Decimal("500000.00"),
                created_by=request.user if request.user.is_authenticated else None,
                updated_by=request.user if request.user.is_authenticated else None,
            )

        # Calculate balance data
        outstanding, invoice_count, avg_days = self._get_customer_balance_data(
            company, customer_name
        )

        # Calculate utilization
        utilization = 0.0
        if credit.credit_limit > 0:
            utilization = float((outstanding / credit.credit_limit) * 100)

        response_data = {
            "customer_name": customer_name,
            "outstanding": float(outstanding),
            "outstanding_display": self._in_lakhs(outstanding),
            "credit_limit": float(credit.credit_limit),
            "credit_limit_display": self._in_lakhs(credit.credit_limit),
            "utilization": round(utilization, 1),
            "invoices": invoice_count,
            "avg_days": avg_days,
            "payment_score": credit.payment_score,
            "risk_level": credit.risk_level,
            "avg_days_to_pay": credit.avg_days_to_pay,
        }

        serializer = CustomerBalanceDetailSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def put(self, request, customer_name, *args, **kwargs):
        """Update customer credit information (full update)"""
        return self._update(request, customer_name, partial=False)

    def patch(self, request, customer_name, *args, **kwargs):
        """Update customer credit information (partial update)"""
        return self._update(request, customer_name, partial=True)

    def _update(self, request, customer_name, partial=False):
        """Update customer credit information"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate input
        serializer = CustomerBalanceUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Get or create credit record
        credit, created = Credit.objects.get_or_create(
            company=company,
            customer_name=customer_name,
            defaults={
                "credit_limit": Decimal("500000.00"),
                "created_by": request.user if request.user.is_authenticated else None,
                "updated_by": request.user if request.user.is_authenticated else None,
            },
        )

        # Update fields
        if "credit_limit" in serializer.validated_data:
            credit.credit_limit = Decimal(
                str(serializer.validated_data["credit_limit"])
            )
        if "payment_score" in serializer.validated_data:
            credit.payment_score = serializer.validated_data["payment_score"]
        if "risk_level" in serializer.validated_data:
            credit.risk_level = serializer.validated_data["risk_level"]

        credit.updated_by = request.user if request.user.is_authenticated else None
        credit.save()

        # Calculate updated balance data
        outstanding, invoice_count, avg_days = self._get_customer_balance_data(
            company, customer_name
        )

        utilization = 0.0
        if credit.credit_limit > 0:
            utilization = float((outstanding / credit.credit_limit) * 100)

        response_data = {
            "customer_name": customer_name,
            "outstanding": float(outstanding),
            "outstanding_display": self._in_lakhs(outstanding),
            "credit_limit": float(credit.credit_limit),
            "credit_limit_display": self._in_lakhs(credit.credit_limit),
            "utilization": round(utilization, 1),
            "invoices": invoice_count,
            "avg_days": avg_days,
            "payment_score": credit.payment_score,
            "risk_level": credit.risk_level,
            "avg_days_to_pay": credit.avg_days_to_pay,
        }

        response_serializer = CustomerBalanceDetailSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)

    def delete(self, request, customer_name, *args, **kwargs):
        """Delete customer credit record"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            credit = Credit.objects.get(company=company, customer_name=customer_name)
            credit.delete()
            return Response(
                {"message": f"Credit record for {customer_name} deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Credit.DoesNotExist:
            return Response(
                {"error": f"Credit record for {customer_name} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
