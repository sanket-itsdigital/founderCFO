from decimal import Decimal

from django.db.models import F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.vendor_balance import (
    VendorBalanceSummarySerializer,
)
from financial.views.api.account_payable.ap_aging import get_company_from_request


class VendorBalanceSummaryView(APIView):
    """API view to get vendor balance summary"""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _format_date(date_value):
        """Format date as DD Mon YYYY"""
        if not date_value:
            return "-"
        return date_value.strftime("%d %b %Y")

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "total_outstanding": 0,
                    "total_outstanding_display": "₹0.00L",
                    "vendors": [],
                },
                status=status.HTTP_200_OK,
            )

        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .filter(amount__gt=F("paid_amount"))
            .select_related("vendor")
        )

        if not bills.exists():
            return Response(
                {
                    "total_outstanding": 0,
                    "total_outstanding_display": "₹0.00L",
                    "vendors": [],
                },
                status=status.HTTP_200_OK,
            )

        vendor_data = {}
        for bill in bills:
            vendor_id = bill.vendor_id
            vendor_name = (
                bill.vendor.name
                if bill.vendor
                else (bill.vendor_name or "Unknown Vendor")
            )
            key = vendor_id or vendor_name

            if key not in vendor_data:
                vendor_data[key] = {
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "outstanding": Decimal("0"),
                    "bill_count": 0,
                    "oldest_bill_date": None,
                }

            entry = vendor_data[key]
            balance = bill.balance_amount
            entry["outstanding"] += balance
            entry["bill_count"] += 1

            bill_date = bill.bill_date
            if not entry["oldest_bill_date"] or bill_date < entry["oldest_bill_date"]:
                entry["oldest_bill_date"] = bill_date

        total_outstanding = sum(v["outstanding"] for v in vendor_data.values())
        vendors = []
        for entry in vendor_data.values():
            percentage = (
                float((entry["outstanding"] / total_outstanding) * 100)
                if total_outstanding > 0
                else 0.0
            )
            oldest_date = entry["oldest_bill_date"]

            vendors.append(
                {
                    "vendor_id": entry["vendor_id"],
                    "vendor_name": entry["vendor_name"],
                    "outstanding": float(entry["outstanding"]),
                    "outstanding_display": self._in_lakhs(entry["outstanding"]),
                    "bill_count": entry["bill_count"],
                    "oldest_bill_date": oldest_date,
                    "oldest_bill_display": (
                        self._format_date(oldest_date) if oldest_date else "-"
                    ),
                    "percentage_of_total": round(percentage, 1),
                }
            )

        # Sort vendors by outstanding descending
        vendors.sort(key=lambda x: x["outstanding"], reverse=True)

        response_data = {
            "total_outstanding": float(total_outstanding),
            "total_outstanding_display": self._in_lakhs(total_outstanding),
            "vendors": vendors,
        }

        serializer = VendorBalanceSummarySerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
