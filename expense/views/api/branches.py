from decimal import Decimal
from collections import defaultdict
from django.db.models import Q, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.views.api.bills import get_company_from_request
from expense.serializers.bills import BillSerializer
from financial.enums import BillsStatusChoices


class BranchesView(APIView):
    """
    Combined API endpoint for all branch-related data.

    GET /api/expense/branches/
    - Returns:
      * Summary KPIs: Total Branches, Total Expenses, Top Branch, Average per Branch
      * All Branches list with detailed information
    - Query parameters:
      * search (optional): Search branches by name
      * page (optional): Page number for all branches list (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores"""
        if amount == 0:
            return "₹0"
        if amount < 1000:
            return f"₹{amount:,.2f}"
        elif amount < 100000:
            return f"₹{amount / 1000:.2f}K"
        elif amount < 10000000:  # Less than 1 crore
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:  # 1 crore or more
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    def get(self, request, *args, **kwargs):
        """Get all branch data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "total_branches": 0,
                        "total_expenses": 0,
                        "total_expenses_display": "₹0",
                        "top_branch": {
                            "branch_name": "",
                            "amount": 0,
                            "amount_display": "₹0",
                            "percentage": 0.0,
                        },
                        "avg_per_branch": 0,
                        "avg_per_branch_display": "₹0",
                    },
                    "all_branches": {
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
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get all bills (excluding cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Apply search filter if provided (for all_branches only)
        bills_for_all = bills
        if search:
            bills_for_all = bills.filter(branch__icontains=search)

        # Group by branch for summary and all branches
        branch_data = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "categories": set(),
                "vendors": set(),
            }
        )

        for bill in bills:
            branch = bill.branch or "Unspecified"
            branch_data[branch]["total_spend"] += bill.total
            branch_data[branch]["bill_count"] += 1
            if bill.category:
                branch_data[branch]["categories"].add(bill.category)
            # Track vendors
            vendor_key = bill.vendor_id or bill.vendor_name
            if vendor_key:
                branch_data[branch]["vendors"].add(vendor_key)

        total_branches = len(branch_data)
        total_expenses = sum(data["total_spend"] for data in branch_data.values())

        # Calculate summary
        top_branch = None
        top_branch_spend = Decimal("0")
        for branch, data in branch_data.items():
            if data["total_spend"] > top_branch_spend:
                top_branch_spend = data["total_spend"]
                top_branch = branch

        top_branch_percentage = (
            float((top_branch_spend / total_expenses) * 100)
            if total_expenses > 0
            else 0.0
        )

        avg_per_branch = (
            total_expenses / Decimal(str(total_branches))
            if total_branches > 0
            else Decimal("0")
        )

        summary = {
            "total_branches": total_branches,
            "total_expenses": float(total_expenses),
            "total_expenses_display": self._format_amount(total_expenses),
            "top_branch": {
                "branch_name": top_branch or "",
                "amount": float(top_branch_spend),
                "amount_display": self._format_amount(top_branch_spend),
                "percentage": round(top_branch_percentage, 1),
            },
            "avg_per_branch": float(avg_per_branch),
            "avg_per_branch_display": self._format_amount(avg_per_branch),
        }

        # All Branches (for table) - with search filter applied
        branch_data_all = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "categories": set(),
                "vendors": set(),
            }
        )

        for bill in bills_for_all:
            branch = bill.branch or "Unspecified"
            branch_data_all[branch]["total_spend"] += bill.total
            branch_data_all[branch]["bill_count"] += 1
            if bill.category:
                branch_data_all[branch]["categories"].add(bill.category)
            # Track vendors
            vendor_key = bill.vendor_id or bill.vendor_name
            if vendor_key:
                branch_data_all[branch]["vendors"].add(vendor_key)

        total_spend_all = sum(data["total_spend"] for data in branch_data_all.values())

        # Convert to list and calculate percentages
        branches_list = []
        for branch, data in branch_data_all.items():
            percentage = (
                float((data["total_spend"] / total_spend_all) * 100)
                if total_spend_all > 0
                else 0.0
            )

            branches_list.append(
                {
                    "branch": branch,
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "bills_count": data["bill_count"],
                    "vendors_count": len(data["vendors"]),
                    "categories_count": len(data["categories"]),
                    "share_percentage": round(percentage, 1),
                }
            )

        # Sort by total spend descending
        branches_list.sort(key=lambda x: x["total_spend"], reverse=True)

        # Add rank/medal indicator for top branch
        for idx, branch_item in enumerate(branches_list, 1):
            branch_item["rank"] = idx
            branch_item["is_top"] = idx == 1

        # Pagination
        total_count = len(branches_list)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_branches = branches_list[start:end]

        all_branches = {
            "count": total_count,
            "results": paginated_branches,
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
                "all_branches": all_branches,
            },
            status=status.HTTP_200_OK,
        )


class BranchBillsView(APIView):
    """
    API endpoint for bills of a specific branch.

    GET /api/expense/branches/<branch_name>/bills/
    - Returns all bills for a specific branch
    - Query parameters:
      * page (optional): Page number (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, branch_name=None, *args, **kwargs):
        """Get bills for a specific branch"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "count": 0,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        if not branch_name:
            return Response(
                {"error": "Branch name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle "Unspecified" branch
        if branch_name.lower() == "unspecified":
            branch_filter = Q(branch__isnull=True) | Q(branch="")
        else:
            branch_filter = Q(branch=branch_name)

        # Get pagination parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get bills for branch
        bills = (
            Bill.objects.filter(company=company)
            .filter(branch_filter)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
            .order_by("-bill_date", "-created_at")
        )

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
