from decimal import Decimal
from datetime import timedelta

from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.payment_scheduler import (
    PaymentSchedulerSerializer,
)
from financial.views.api.account_payable.ap_aging import get_company_from_request


class PaymentSchedulerView(APIView):
    """
    API view to get Payment Scheduler data.

    Returns bills grouped by:
    - Overdue
    - Due This Week
    - Due Next Week
    - Upcoming
    - Selected for Payment (empty initially, managed by frontend)
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
            return PaymentSchedulerView._in_lakhs(amount)
        else:
            return PaymentSchedulerView._in_thousands(amount)

    @staticmethod
    def _format_date(date_value):
        """Format date as DD Mon YYYY"""
        if not date_value:
            return "-"
        return date_value.strftime("%d %b %Y")

    @staticmethod
    def _calculate_discount(bill, today):
        """Calculate early payment discount"""
        # If bill is not overdue and within discount window
        if bill.due_date >= today:
            days_until_due = (bill.due_date - today).days
            days_since_bill = (today - bill.bill_date).days

            # Example: 2-3% discount if paid within 10 days of bill date
            if days_since_bill <= 10 and days_until_due > 0:
                discount_pct = Decimal("2.0")  # 2% discount
                discount_amt = bill.balance_amount * (discount_pct / Decimal("100"))
                return discount_pct, discount_amt
            elif days_since_bill <= 15 and days_until_due > 0:
                discount_pct = Decimal("1.0")  # 1% discount
                discount_amt = bill.balance_amount * (discount_pct / Decimal("100"))
                return discount_pct, discount_amt

        return None, Decimal("0")

    @staticmethod
    def _get_status_label(bill, days_overdue, days_until_due):
        """Get status label for bill"""
        if days_overdue > 0:
            return "Overdue"
        elif days_until_due == 0:
            return "Due Today"
        elif days_until_due <= 7:
            return "Due Soon"
        else:
            return "Upcoming"

    def _categorize_bills(self, bills, today):
        """Categorize bills into groups"""
        overdue = []
        due_this_week = []
        due_next_week = []
        upcoming = []

        # Calculate week boundaries
        end_of_this_week = today + timedelta(days=(6 - today.weekday()))
        end_of_next_week = end_of_this_week + timedelta(days=7)

        for bill in bills:
            balance = bill.balance_amount
            if balance <= 0:
                continue

            days_overdue = (today - bill.due_date).days if bill.due_date < today else 0
            days_until_due = (
                (bill.due_date - today).days if bill.due_date >= today else 0
            )

            # Calculate discount
            discount_pct, discount_amt = self._calculate_discount(bill, today)

            # Format days display
            if days_overdue > 0:
                days_display = f"{days_overdue} overdue"
            elif days_until_due == 0:
                days_display = "Due today"
            elif days_until_due == 1:
                days_display = "Due tomorrow"
            else:
                days_display = f"{days_until_due} days"

            bill_data = {
                "bill_id": str(bill.id),
                "bill_number": bill.bill_number,
                "vendor_id": str(bill.vendor.id) if bill.vendor else None,
                "vendor_name": bill.get_vendor_name(),
                "due_date": bill.due_date,
                "due_date_display": self._format_date(bill.due_date),
                "days_overdue": days_overdue,
                "days_until_due": days_until_due,
                "days_display": days_display,
                "amount": float(balance),
                "amount_display": self._format_amount_display(balance),
                "discount_percentage": float(discount_pct) if discount_pct else None,
                "discount_amount": float(discount_amt) if discount_amt else None,
                "discount_display": (
                    f"Save {self._format_amount_display(discount_amt)}"
                    if discount_amt > 0
                    else "-"
                ),
                "status": self._get_status_label(bill, days_overdue, days_until_due),
                "is_selected": False,  # Frontend will manage selection
            }

            # Categorize
            if days_overdue > 0:
                overdue.append(bill_data)
            elif bill.due_date <= end_of_this_week:
                due_this_week.append(bill_data)
            elif bill.due_date <= end_of_next_week:
                due_next_week.append(bill_data)
            else:
                upcoming.append(bill_data)

        return overdue, due_this_week, due_next_week, upcoming

    def _create_group(self, group_name, bills_list):
        """Create a group object with summary"""
        total_amount = sum(Decimal(str(b["amount"])) for b in bills_list)
        total_discount = sum(
            Decimal(str(b.get("discount_amount", 0) or 0)) for b in bills_list
        )

        return {
            "group_name": group_name,
            "bill_count": len(bills_list),
            "total_amount": float(total_amount),
            "total_amount_display": self._in_lakhs(total_amount),
            "potential_discount": float(total_discount) if total_discount > 0 else None,
            "potential_discount_display": (
                self._format_amount_display(total_discount)
                if total_discount > 0
                else None
            ),
            "bills": bills_list,
        }

    def get(self, request, *args, **kwargs):
        """Get payment scheduler data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary_cards": [
                        {
                            "title": "Overdue",
                            "amount": 0.0,
                            "amount_display": "₹0.00L",
                            "bill_count": 0,
                            "icon": "overdue",
                        },
                        {
                            "title": "Due This Week",
                            "amount": 0.0,
                            "amount_display": "₹0.00L",
                            "bill_count": 0,
                            "icon": "due_this_week",
                        },
                        {
                            "title": "Due Next Week",
                            "amount": 0.0,
                            "amount_display": "₹0.00L",
                            "bill_count": 0,
                            "icon": "due_next_week",
                        },
                    ],
                    "overdue": self._create_group("Overdue", []),
                    "due_this_week": self._create_group("Due This Week", []),
                    "due_next_week": self._create_group("Due Next Week", []),
                    "upcoming": self._create_group("Upcoming", []),
                    "selected_for_payment": self._create_group(
                        "Selected for Payment", []
                    ),
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

        # Categorize bills
        overdue, due_this_week, due_next_week, upcoming = self._categorize_bills(
            bills, today
        )

        # Sort overdue by days overdue (descending)
        overdue.sort(key=lambda x: x["days_overdue"], reverse=True)

        # Sort others by due date (ascending)
        due_this_week.sort(key=lambda x: x["due_date"])
        due_next_week.sort(key=lambda x: x["due_date"])
        upcoming.sort(key=lambda x: x["due_date"])

        # Create groups
        overdue_group = self._create_group("Overdue", overdue)
        due_this_week_group = self._create_group("Due This Week", due_this_week)
        due_next_week_group = self._create_group("Due Next Week", due_next_week)
        upcoming_group = self._create_group("Upcoming", upcoming)
        selected_group = self._create_group("Selected for Payment", [])

        # Create summary cards
        summary_cards = [
            {
                "title": "Overdue",
                "amount": overdue_group["total_amount"],
                "amount_display": overdue_group["total_amount_display"],
                "bill_count": overdue_group["bill_count"],
                "icon": "overdue",
            },
            {
                "title": "Due This Week",
                "amount": due_this_week_group["total_amount"],
                "amount_display": due_this_week_group["total_amount_display"],
                "bill_count": due_this_week_group["bill_count"],
                "icon": "due_this_week",
            },
            {
                "title": "Due Next Week",
                "amount": due_next_week_group["total_amount"],
                "amount_display": due_next_week_group["total_amount_display"],
                "bill_count": due_next_week_group["bill_count"],
                "icon": "due_next_week",
            },
        ]

        response_data = {
            "summary_cards": summary_cards,
            "overdue": overdue_group,
            "due_this_week": due_this_week_group,
            "due_next_week": due_next_week_group,
            "upcoming": upcoming_group,
            "selected_for_payment": selected_group,
        }

        serializer = PaymentSchedulerSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
