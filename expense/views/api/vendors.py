from decimal import Decimal
from collections import defaultdict
from django.db.models import Q, Count, Avg, Sum
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.views.api.bills import get_company_from_request
from expense.serializers.bills import BillSerializer
from financial.enums import BillsStatusChoices


class VendorsView(APIView):
    """
    Combined API endpoint for all vendor-related data.

    GET /api/expense/vendors/
    - Returns:
      * Summary KPIs: Total Vendors, Top Vendor Spend, Average per Vendor
      * Top Vendors by Spend (for bar chart)
      * All Vendors list with detailed information
    - Query parameters:
      * search (optional): Search vendors by name
      * top_limit (optional): Number of top vendors to return (default: 10)
      * page (optional): Page number for all vendors list (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs"""
        if amount == 0:
            return "₹0"
        if amount < 1000:
            return f"₹{amount:,.2f}"
        elif amount < 100000:
            return f"₹{amount / 1000:.2f}K"
        else:
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request, *args, **kwargs):
        """Get all vendor data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "total_vendors": 0,
                        "top_vendor_spend": {
                            "vendor_name": "",
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "avg_per_vendor": 0,
                        "avg_per_vendor_display": "₹0",
                    },
                    "top_vendors": [],
                    "all_vendors": {
                        "count": 0,
                        "results": [],
                        "total_spend": 0,
                        "total_spend_display": "₹0",
                    },
                },
                status=status.HTTP_200_OK,
            )

        # Get query parameters
        search = request.query_params.get("search", "").strip()
        top_limit = int(request.query_params.get("top_limit", 10))
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get all bills (excluding cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Apply search filter if provided (for all_vendors only)
        bills_for_all = bills
        if search:
            bills_for_all = bills.filter(
                Q(vendor__name__icontains=search) | Q(vendor_name__icontains=search)
            )

        # Group by vendor for summary and top vendors
        vendor_data = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "vendor_name": None,
                "vendor_id": None,
                "categories": set(),
            }
        )

        for bill in bills:
            vendor_id = bill.vendor_id
            vendor_name = (
                bill.vendor.name
                if bill.vendor
                else (bill.vendor_name or "Unknown Vendor")
            )
            vendor_key = vendor_id or vendor_name

            vendor_data[vendor_key]["total_spend"] += bill.total
            vendor_data[vendor_key]["bill_count"] += 1
            if not vendor_data[vendor_key]["vendor_name"]:
                vendor_data[vendor_key]["vendor_name"] = vendor_name
            if not vendor_data[vendor_key]["vendor_id"]:
                vendor_data[vendor_key]["vendor_id"] = vendor_id
            if bill.category:
                vendor_data[vendor_key]["categories"].add(bill.category)

        total_vendors = len(vendor_data)
        total_spend = sum(data["total_spend"] for data in vendor_data.values())

        # Calculate summary
        top_vendor = None
        top_vendor_spend = Decimal("0")
        for vendor_key, data in vendor_data.items():
            if data["total_spend"] > top_vendor_spend:
                top_vendor_spend = data["total_spend"]
                top_vendor = data["vendor_name"]

        avg_per_vendor = (
            total_spend / Decimal(str(total_vendors))
            if total_vendors > 0
            else Decimal("0")
        )

        summary = {
            "total_vendors": total_vendors,
            "top_vendor_spend": {
                "vendor_name": top_vendor or "",
                "amount": float(top_vendor_spend),
                "amount_display": self._format_amount(top_vendor_spend),
            },
            "avg_per_vendor": float(avg_per_vendor),
            "avg_per_vendor_display": self._format_amount(avg_per_vendor),
        }

        # Get top vendors by spend
        sorted_vendors = sorted(
            vendor_data.items(), key=lambda x: x[1]["total_spend"], reverse=True
        )[:top_limit]

        top_vendors = []
        for vendor_key, data in sorted_vendors:
            top_vendors.append(
                {
                    "vendor_name": data["vendor_name"],
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                }
            )

        # Get all vendors (with search filter applied)
        vendor_data_all = defaultdict(
            lambda: {
                "vendor_name": None,
                "vendor_id": None,
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "categories": set(),
            }
        )

        for bill in bills_for_all:
            vendor_id = bill.vendor_id
            vendor_name = (
                bill.vendor.name
                if bill.vendor
                else (bill.vendor_name or "Unknown Vendor")
            )
            vendor_key = vendor_id or vendor_name

            vendor_data_all[vendor_key]["vendor_name"] = vendor_name
            vendor_data_all[vendor_key]["vendor_id"] = vendor_id
            vendor_data_all[vendor_key]["total_spend"] += bill.total
            vendor_data_all[vendor_key]["bill_count"] += 1
            if bill.category:
                vendor_data_all[vendor_key]["categories"].add(bill.category)

        total_spend_all = sum(data["total_spend"] for data in vendor_data_all.values())

        # Convert to list and calculate percentages
        vendors_list = []
        for vendor_key, data in vendor_data_all.items():
            avg_per_bill = (
                data["total_spend"] / Decimal(str(data["bill_count"]))
                if data["bill_count"] > 0
                else Decimal("0")
            )
            percentage = (
                float((data["total_spend"] / total_spend_all) * 100)
                if total_spend_all > 0
                else 0.0
            )

            categories = list(data["categories"])
            primary_category = categories[0] if categories else ""

            vendors_list.append(
                {
                    "vendor_id": str(data["vendor_id"]) if data["vendor_id"] else None,
                    "vendor_name": data["vendor_name"],
                    "categories": primary_category,
                    "categories_list": categories[:3],  # Top 3 categories
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "bills_count": data["bill_count"],
                    "avg_per_bill": float(avg_per_bill),
                    "avg_per_bill_display": self._format_amount(avg_per_bill),
                    "percentage_of_total": round(percentage, 1),
                }
            )

        # Sort by total spend descending
        vendors_list.sort(key=lambda x: x["total_spend"], reverse=True)

        # Add rank
        for idx, vendor in enumerate(vendors_list, 1):
            vendor["rank"] = idx

        # Pagination
        total_count = len(vendors_list)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_vendors = vendors_list[start:end]

        all_vendors = {
            "count": total_count,
            "results": paginated_vendors,
            "total_spend": float(total_spend_all),
            "total_spend_display": self._format_amount(total_spend_all),
            "page": page,
            "page_size": page_size,
            "next": f"?page={page + 1}" if end < total_count else None,
            "previous": f"?page={page - 1}" if page > 1 else None,
        }

        return Response(
            {
                "summary": summary,
                "top_vendors": top_vendors,
                "all_vendors": all_vendors,
            },
            status=status.HTTP_200_OK,
        )


class VendorBillsView(APIView):
    """
    API endpoint for bills of a specific vendor.

    GET /api/expense/vendors/<vendor_id>/bills/
    - Returns all bills for a specific vendor
    - Query parameters:
      * vendor_name (optional): Filter by vendor name if vendor_id is not available
      * page (optional): Page number (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id=None, *args, **kwargs):
        """Get bills for a specific vendor"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "count": 0,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get pagination parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        vendor_name = request.query_params.get("vendor_name", "").strip()

        # Get bills for vendor
        bills = Bill.objects.filter(company=company).exclude(
            status=BillsStatusChoices.CANCELLED
        )

        if vendor_id:
            bills = bills.filter(vendor_id=vendor_id)
        elif vendor_name:
            bills = bills.filter(
                Q(vendor__name__iexact=vendor_name) | Q(vendor_name__iexact=vendor_name)
            )
        else:
            return Response(
                {"error": "Either vendor_id or vendor_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bills = bills.select_related("vendor").order_by("-bill_date", "-created_at")

        # Pagination
        total_count = bills.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated_bills = bills[start:end]

        serializer = BillSerializer(paginated_bills, many=True)

        return Response(
            {
                "count": total_count,
                "results": serializer.data,
                "page": page,
                "page_size": page_size,
                "next": f"?page={page + 1}" if end < total_count else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
            },
            status=status.HTTP_200_OK,
        )
