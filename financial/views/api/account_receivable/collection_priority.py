from decimal import Decimal
from collections import defaultdict

from django.db.models import F, Min
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from revenue.models.invoice import Invoice
from financial.models.account_receivable.credit import Credit
from financial.enums import InvoicesStatusChoices, RiskLevelChoices

from financial.serializers.account_receivable.collection_priority import (
    CollectionPrioritySerializer,
)


def get_company_from_request(request):
    """Helper function to get company from request"""
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return None
    # Try to get the first company owned by the user
    return Company.objects.filter(owner=request.user).first()


class CollectionPriorityView(APIView):
    """
    API view to get Collection Priority dashboard data.

    Returns:
    - Summary metrics (Critical count, High Priority count, Total Overdue, Expected Recovery, Total Customers)
    - Customer list with priority, outstanding amounts, days overdue, recovery %, and recommended actions
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
    def _calculate_priority(days_overdue, outstanding_amount, risk_level):
        """Calculate collection priority based on days overdue, amount, and risk level"""
        # Critical: 90+ days overdue OR (60+ days AND high risk) OR (outstanding > 50L AND 30+ days)
        if (
            days_overdue >= 90
            or (days_overdue >= 60 and risk_level == RiskLevelChoices.HIGH)
            or (outstanding_amount >= Decimal("5000000") and days_overdue >= 30)
        ):
            return "Critical", "#EF4444"  # Red

        # High Priority: 60+ days overdue OR (30+ days AND medium/high risk) OR (outstanding > 20L AND 15+ days)
        elif (
            days_overdue >= 60
            or (
                days_overdue >= 30
                and risk_level in [RiskLevelChoices.MEDIUM, RiskLevelChoices.HIGH]
            )
            or (outstanding_amount >= Decimal("2000000") and days_overdue >= 15)
        ):
            return "High", "#F59E0B"  # Orange/Amber

        # Medium Priority: 30+ days overdue OR medium risk
        elif days_overdue >= 30 or risk_level == RiskLevelChoices.MEDIUM:
            return "Medium", "#F97316"  # Light Orange

        # Low Priority: Everything else
        else:
            return "Low", "#10B981"  # Green

    @staticmethod
    def _calculate_recovery_percentage(priority, days_overdue, risk_level):
        """Calculate estimated recovery percentage based on priority and risk"""
        # Base recovery percentages
        if priority == "Critical":
            if days_overdue >= 120:
                return 30.0  # Very old, low recovery
            elif days_overdue >= 90:
                return 40.0  # Old, moderate recovery
            else:
                return 50.0
        elif priority == "High":
            if risk_level == RiskLevelChoices.HIGH:
                return 50.0
            else:
                return 60.0
        elif priority == "Medium":
            return 70.0
        else:
            return 85.0

    @staticmethod
    def _get_recommended_action(priority, days_overdue):
        """Get recommended action based on priority and days overdue"""
        if priority == "Critical":
            if days_overdue >= 90:
                return "Escalate to management"
            else:
                return "Immediate follow-up required"
        elif priority == "High":
            if days_overdue >= 60:
                return "Schedule payment plan discussion"
            else:
                return "Send reminder notice"
        elif priority == "Medium":
            return "Standard follow-up"
        else:
            return "Monitor payment status"

    def _get_queryset(self, request):
        """Get filtered invoices queryset for the company"""
        company = get_company_from_request(request)
        if not company:
            return Invoice.objects.none()

        # Get all overdue invoices with outstanding balance
        queryset = (
            Invoice.objects.filter(company=company)
            .exclude(
                status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
            )
            .filter(due_date__lt=timezone.now().date())
        )

        return queryset

    def get(self, request, *args, **kwargs):
        """Calculate and return collection priority data"""
        invoices = self._get_queryset(request)

        if not invoices.exists():
            # Return empty response
            return Response(
                {
                    "summary": {
                        "critical_count": 0,
                        "high_priority_count": 0,
                        "total_overdue": 0,
                        "total_overdue_display": "₹0.00Cr",
                        "expected_recovery": 0,
                        "expected_recovery_display": "₹0.00L",
                        "total_customers": 0,
                    },
                    "customers": [],
                    "collection_tips": [
                        "Focus on Critical and High priority customers first",
                        "For 90+ days overdue, consider offering payment plans",
                        "Early payment discounts can accelerate collections by 20-30%",
                        "Regular follow-up calls improve recovery probability by 15%",
                    ],
                }
            )

        today = timezone.now().date()

        # Group invoices by customer
        customer_data = defaultdict(
            lambda: {
                "invoices": [],
                "outstanding": Decimal("0"),
                "oldest_due_date": None,
                "days_overdue": 0,
            }
        )

        # Get credit information for all customers
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "critical_count": 0,
                        "high_priority_count": 0,
                        "total_overdue": 0,
                        "total_overdue_display": "₹0.00Cr",
                        "expected_recovery": 0,
                        "expected_recovery_display": "₹0.00L",
                        "total_customers": 0,
                    },
                    "customers": [],
                    "collection_tips": [],
                }
            )

        # Fetch all credit records for customers
        customer_names = set()
        for invoice in invoices:
            customer_names.add(invoice.customer_name)

        credits = {
            credit.customer_name: credit
            for credit in Credit.objects.filter(
                company=company, customer_name__in=customer_names
            )
        }

        # Process invoices
        for invoice in invoices:
            customer_name = invoice.customer_name
            # Revenue Invoice has no paid tracking; treat full total as outstanding
            balance = invoice.total_amount
            customer_data[customer_name]["invoices"].append(invoice)
            customer_data[customer_name]["outstanding"] += balance

            # Track oldest due date
            if (
                customer_data[customer_name]["oldest_due_date"] is None
                or invoice.due_date < customer_data[customer_name]["oldest_due_date"]
            ):
                customer_data[customer_name]["oldest_due_date"] = invoice.due_date

        # Calculate days overdue and other metrics for each customer
        customers_list = []
        priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        total_overdue = Decimal("0")
        total_expected_recovery = Decimal("0")

        for customer_name, data in customer_data.items():
            # Calculate days overdue from oldest invoice
            days_overdue = (
                (today - data["oldest_due_date"]).days if data["oldest_due_date"] else 0
            )
            data["days_overdue"] = days_overdue

            # Get risk level from credit model or default to LOW
            credit = credits.get(customer_name)
            risk_level = credit.risk_level if credit else RiskLevelChoices.LOW

            # Calculate priority
            priority, priority_color = self._calculate_priority(
                days_overdue, data["outstanding"], risk_level
            )
            priority_counts[priority] += 1

            # Calculate recovery percentage
            recovery_percentage = self._calculate_recovery_percentage(
                priority, days_overdue, risk_level
            )

            # Calculate expected recovery
            expected_recovery = data["outstanding"] * Decimal(
                str(recovery_percentage / 100)
            )
            total_expected_recovery += expected_recovery

            # Get recommended action
            recommended_action = self._get_recommended_action(priority, days_overdue)

            # Add to customers list
            customers_list.append(
                {
                    "customer_name": customer_name,
                    "invoice_count": len(data["invoices"]),
                    "priority": priority,
                    "priority_color": priority_color,
                    "outstanding": float(data["outstanding"]),
                    "outstanding_display": self._in_lakhs(data["outstanding"]),
                    "days_overdue": days_overdue,
                    "recovery_percentage": recovery_percentage,
                    "recommended_action": recommended_action,
                }
            )

            total_overdue += data["outstanding"]

        # Sort customers by priority (Critical first, then High, Medium, Low)
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        customers_list.sort(
            key=lambda x: (priority_order.get(x["priority"], 99), -x["days_overdue"])
        )

        # Format total overdue (use crores if >= 1Cr, otherwise lakhs)
        if total_overdue >= Decimal("10000000"):
            total_overdue_display = self._in_crores(total_overdue)
        else:
            total_overdue_display = self._in_lakhs(total_overdue)

        # Build summary
        summary = {
            "critical_count": priority_counts["Critical"],
            "high_priority_count": priority_counts["High"],
            "total_overdue": float(total_overdue),
            "total_overdue_display": total_overdue_display,
            "expected_recovery": float(total_expected_recovery),
            "expected_recovery_display": self._in_lakhs(total_expected_recovery),
            "total_customers": len(customers_list),
        }

        # Collection Tips
        collection_tips = [
            "Focus on Critical and High priority customers first",
            "For 90+ days overdue, consider offering payment plans",
            "Early payment discounts can accelerate collections by 20-30%",
            "Regular follow-up calls improve recovery probability by 15%",
        ]

        response_data = {
            "summary": summary,
            "customers": customers_list,
            "collection_tips": collection_tips,
        }

        # Validate with serializer
        serializer = CollectionPrioritySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
