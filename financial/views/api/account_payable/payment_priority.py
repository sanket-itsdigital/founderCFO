from decimal import Decimal

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.payment_priority import (
    PaymentPriorityQueueSerializer,
)
from financial.views.api.account_payable.ap_aging import get_company_from_request


class PaymentPriorityQueueView(APIView):
    """
    API view to get Payment Priority Queue.

    Returns bills prioritized by overdue status and early payment discounts.
    Priority levels:
    - Critical: 45+ days overdue
    - Overdue: Less than 45 days overdue but still overdue
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
    def _in_thousands(amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return PaymentPriorityQueueView._in_lakhs(amount)
        else:
            return PaymentPriorityQueueView._in_thousands(amount)

    @staticmethod
    def _format_date(date_value):
        """Format date as DD Mon YYYY"""
        if not date_value:
            return "-"
        return date_value.strftime("%d %b %Y")

    @staticmethod
    def _calculate_priority(days_overdue):
        """Calculate payment priority based on overdue days"""
        if days_overdue >= 45:
            return "Critical", "#EF4444"  # Red
        elif days_overdue > 0:
            return "Overdue", "#EF4444"  # Red
        else:
            return "Current", "#10B981"  # Green

    @staticmethod
    def _calculate_discount(due_date, bill_date, vendor_payment_terms=None):
        """
        Calculate early payment discount percentage.
        This is a placeholder - in real implementation, this would come from:
        - Vendor payment terms
        - Discount programs
        - Bill-specific discounts
        """
        # Placeholder logic: If payment is made within 10 days of bill date, 2-3% discount
        # In production, this should come from vendor.payment_terms or discount programs
        today = timezone.now().date()
        days_since_bill = (today - bill_date).days

        # Example: If bill is less than 10 days old and not overdue, offer discount
        if days_since_bill <= 10 and due_date >= today:
            # Return a discount between 2-3% (example)
            return 2.0  # Default 2% discount
        elif days_since_bill <= 15 and due_date >= today:
            return 1.0  # 1% discount
        else:
            return None  # No discount

    def get(self, request, *args, **kwargs):
        """Get payment priority queue"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "bills": [],
                    "summary": {
                        "total_bills": 0,
                        "total_amount": 0,
                        "total_amount_display": "₹0.00L",
                        "critical_count": 0,
                        "overdue_count": 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()

        # Get all unpaid bills (not fully paid or cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED])
            .filter(amount__gt=F("paid_amount"))
            .select_related("vendor")
            .order_by("due_date")
        )

        if not bills.exists():
            return Response(
                {
                    "bills": [],
                    "summary": {
                        "total_bills": 0,
                        "total_amount": 0,
                        "total_amount_display": "₹0.00L",
                        "critical_count": 0,
                        "overdue_count": 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        bills_list = []
        total_amount = Decimal("0")
        critical_count = 0
        overdue_count = 0

        for bill in bills:
            balance = bill.balance_amount
            if balance <= 0:
                continue

            # Calculate days overdue
            days_overdue = (today - bill.due_date).days if bill.due_date < today else 0

            # Calculate priority
            priority, priority_color = self._calculate_priority(days_overdue)
            if priority == "Critical":
                critical_count += 1
            elif priority == "Overdue":
                overdue_count += 1

            # Calculate discount
            discount_percentage = self._calculate_discount(
                bill.due_date,
                bill.bill_date,
                bill.vendor.payment_terms if bill.vendor else None,
            )

            # Format days display
            if days_overdue > 0:
                days_display = f"{days_overdue} overdue"
            else:
                days_until_due = (bill.due_date - today).days
                if days_until_due == 0:
                    days_display = "Due today"
                elif days_until_due == 1:
                    days_display = "Due tomorrow"
                else:
                    days_display = f"Due in {days_until_due} days"

            bills_list.append(
                {
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "vendor_id": str(bill.vendor.id) if bill.vendor else None,
                    "vendor_name": bill.get_vendor_name(),
                    "due_date": bill.due_date,
                    "due_date_display": self._format_date(bill.due_date),
                    "days_overdue": days_overdue,
                    "days_display": days_display,
                    "amount_due": float(balance),
                    "amount_due_display": self._format_amount_display(balance),
                    "discount_percentage": discount_percentage,
                    "discount_display": (
                        f"{discount_percentage}%" if discount_percentage else "-"
                    ),
                    "priority": priority,
                    "priority_color": priority_color,
                }
            )

            total_amount += balance

        # Sort bills by priority (Critical first, then Overdue, then by days overdue descending)
        def sort_key(bill):
            priority_order = {"Critical": 0, "Overdue": 1, "Current": 2}
            return (priority_order.get(bill["priority"], 99), -bill["days_overdue"])

        bills_list.sort(key=sort_key)

        response_data = {
            "bills": bills_list,
            "summary": {
                "total_bills": len(bills_list),
                "total_amount": float(total_amount),
                "total_amount_display": self._in_lakhs(total_amount),
                "critical_count": critical_count,
                "overdue_count": overdue_count,
            },
        }

        serializer = PaymentPriorityQueueSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
