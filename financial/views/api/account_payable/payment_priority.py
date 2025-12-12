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
    All data comes from the Bill model (expenses.bills).
    Priority levels:
    - Critical: 30+ days overdue
    - High: 15-29 days overdue
    - Medium: 1-14 days overdue
    - Low: Not overdue
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
        if days_overdue >= 30:
            return "Critical", "#EF4444"  # Red
        elif days_overdue >= 15:
            return "High", "#F59E0B"  # Orange
        elif days_overdue > 0:
            return "Medium", "#F97316"  # Orange-red
        else:
            return "Low", "#10B981"  # Green

    @staticmethod
    def _calculate_discount(bill, today):
        """
        Calculate early payment discount percentage based on bill data.
        Discount logic:
        - If bill is not overdue and paid within 10 days of bill date: 2-3% discount
        - If bill is not overdue and paid within 15 days of bill date: 1% discount
        """
        if not bill.bill_date:
            return None

        days_since_bill = (today - bill.bill_date).days
        days_until_due = (bill.due_date - today).days if bill.due_date else 0

        # Only offer discount if bill is not overdue
        if bill.due_date and bill.due_date >= today:
            # If payment is made within 10 days of bill date, offer 2-3% discount
            if days_since_bill <= 10 and days_until_due > 0:
                # Return 2-3% discount (use 2% as default, can vary by vendor)
                return 2.0
            # If payment is made within 15 days of bill date, offer 1% discount
            elif days_since_bill <= 15 and days_until_due > 0:
                return 1.0

        return None

    def get(self, request, *args, **kwargs):
        """Get payment priority queue - all data from Bill model"""
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
                        "high_count": 0,
                        "medium_count": 0,
                        "overdue_count": 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        today = timezone.now().date()

        # Get all unpaid bills from Bill model (not fully paid or cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status__in=[BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED])
            .filter(total__gt=F("paid_amount"))  # Use total instead of amount
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
                        "high_count": 0,
                        "medium_count": 0,
                        "overdue_count": 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        bills_list = []
        total_amount = Decimal("0")
        critical_count = 0
        high_count = 0
        medium_count = 0
        overdue_count = 0

        for bill in bills:
            # Get balance amount from Bill model
            balance = bill.balance_amount  # This uses total - paid_amount
            if balance <= 0:
                continue

            # Calculate days overdue from Bill model's due_date
            days_overdue = (
                (today - bill.due_date).days
                if bill.due_date and bill.due_date < today
                else 0
            )

            # Calculate priority
            priority, priority_color = self._calculate_priority(days_overdue)
            if priority == "Critical":
                critical_count += 1
            elif priority == "High":
                high_count += 1
            elif priority == "Medium":
                medium_count += 1

            if days_overdue > 0:
                overdue_count += 1

            # Calculate discount based on bill data
            discount_percentage = self._calculate_discount(bill, today)

            # Format days display - match image format: "X overdue"
            if days_overdue > 0:
                days_display = f"{days_overdue} overdue"
            else:
                days_until_due = (bill.due_date - today).days if bill.due_date else 0
                if days_until_due == 0:
                    days_display = "Due today"
                elif days_until_due == 1:
                    days_display = "Due tomorrow"
                else:
                    days_display = f"Due in {days_until_due} days"

            # Get vendor name from Bill model
            vendor_name = bill.get_vendor_name()

            bills_list.append(
                {
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "vendor_id": str(bill.vendor.id) if bill.vendor else None,
                    "vendor_name": vendor_name,
                    "due_date": bill.due_date,
                    "due_date_display": self._format_date(bill.due_date),
                    "days_overdue": days_overdue,
                    "days_display": days_display,
                    "amount_due": float(balance),
                    "amount_due_display": self._format_amount_display(balance),
                    "discount_percentage": discount_percentage,
                    "discount_display": (
                        f"{int(discount_percentage)}%" if discount_percentage else "-"
                    ),
                    "priority": priority,
                    "priority_color": priority_color,
                }
            )

            total_amount += balance

        # Sort bills by priority (Critical first, then by days overdue descending)
        def sort_key(bill_item):
            priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
            return (
                priority_order.get(bill_item["priority"], 99),
                -bill_item["days_overdue"],
            )

        bills_list.sort(key=sort_key)

        response_data = {
            "bills": bills_list,
            "summary": {
                "total_bills": len(bills_list),
                "total_amount": float(total_amount),
                "total_amount_display": self._in_lakhs(total_amount),
                "critical_count": critical_count,
                "high_count": high_count,
                "medium_count": medium_count,
                "overdue_count": overdue_count,
            },
        }

        serializer = PaymentPriorityQueueSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
