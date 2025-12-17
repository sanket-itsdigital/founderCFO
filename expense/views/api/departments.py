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


class DepartmentsView(APIView):
    """
    Combined API endpoint for all department-related data.

    GET /api/expense/departments/
    - Returns:
      * Summary KPIs: Total Departments, Top Department Spend, Average per Department
      * Spend by Department (for bar chart)
      * Department Distribution (for donut chart)
      * All Departments list with detailed information
    - Query parameters:
      * search (optional): Search departments by name
      * page (optional): Page number for all departments list (default: 1)
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
        """Get all department data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "total_departments": 0,
                        "top_department": {
                            "department_name": "",
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "avg_per_department": 0,
                        "avg_per_department_display": "₹0",
                    },
                    "spend_by_department": [],
                    "department_distribution": [],
                    "all_departments": {
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

        # Apply search filter if provided (for all_departments only)
        bills_for_all = bills
        if search:
            bills_for_all = bills.filter(department__icontains=search)

        # Group by department for summary, spend by department, and distribution
        department_data = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "categories": set(),
                "vendors": set(),
            }
        )

        for bill in bills:
            department = bill.department or "Unassigned"
            department_data[department]["total_spend"] += bill.total
            department_data[department]["bill_count"] += 1
            if bill.category:
                department_data[department]["categories"].add(bill.category)
            # Track vendors
            vendor_key = bill.vendor_id or bill.vendor_name
            if vendor_key:
                department_data[department]["vendors"].add(vendor_key)

        total_departments = len(department_data)
        total_spend = sum(data["total_spend"] for data in department_data.values())

        # Calculate summary
        top_department = None
        top_department_spend = Decimal("0")
        for department, data in department_data.items():
            if data["total_spend"] > top_department_spend:
                top_department_spend = data["total_spend"]
                top_department = department

        avg_per_department = (
            total_spend / Decimal(str(total_departments))
            if total_departments > 0
            else Decimal("0")
        )

        summary = {
            "total_departments": total_departments,
            "top_department": {
                "department_name": top_department or "",
                "amount": float(top_department_spend),
                "amount_display": self._format_amount(top_department_spend),
            },
            "avg_per_department": float(avg_per_department),
            "avg_per_department_display": self._format_amount(avg_per_department),
        }

        # Spend by Department (for bar chart) - sorted by spend descending
        sorted_departments = sorted(
            department_data.items(), key=lambda x: x[1]["total_spend"], reverse=True
        )

        spend_by_department = []
        for department, data in sorted_departments:
            spend_by_department.append(
                {
                    "department": department,
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                }
            )

        # Department Distribution (for donut chart)
        department_distribution = []
        for department, data in sorted_departments:
            percentage = (
                float((data["total_spend"] / total_spend) * 100)
                if total_spend > 0
                else 0.0
            )
            department_distribution.append(
                {
                    "department": department,
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "percentage": round(percentage, 1),
                }
            )

        # All Departments (for table) - with search filter applied
        department_data_all = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "categories": set(),
                "vendors": set(),
            }
        )

        for bill in bills_for_all:
            department = bill.department or "Unassigned"
            department_data_all[department]["total_spend"] += bill.total
            department_data_all[department]["bill_count"] += 1
            if bill.category:
                department_data_all[department]["categories"].add(bill.category)
            # Track vendors
            vendor_key = bill.vendor_id or bill.vendor_name
            if vendor_key:
                department_data_all[department]["vendors"].add(vendor_key)

        total_spend_all = sum(
            data["total_spend"] for data in department_data_all.values()
        )

        # Convert to list and calculate percentages
        departments_list = []
        for department, data in department_data_all.items():
            percentage = (
                float((data["total_spend"] / total_spend_all) * 100)
                if total_spend_all > 0
                else 0.0
            )

            departments_list.append(
                {
                    "department": department,
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "bills_count": data["bill_count"],
                    "categories_count": len(data["categories"]),
                    "vendors_count": len(data["vendors"]),
                    "percentage_of_total": round(percentage, 1),
                }
            )

        # Sort by total spend descending
        departments_list.sort(key=lambda x: x["total_spend"], reverse=True)

        # Pagination
        total_count = len(departments_list)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_departments = departments_list[start:end]

        all_departments = {
            "count": total_count,
            "results": paginated_departments,
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
                "spend_by_department": spend_by_department,
                "department_distribution": department_distribution,
                "all_departments": all_departments,
            },
            status=status.HTTP_200_OK,
        )


class DepartmentBillsView(APIView):
    """
    API endpoint for bills of a specific department.

    GET /api/expense/departments/<department_name>/bills/
    - Returns all bills for a specific department
    - Query parameters:
      * page (optional): Page number (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, department_name=None, *args, **kwargs):
        """Get bills for a specific department"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "count": 0,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        if not department_name:
            return Response(
                {"error": "Department name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle "Unassigned" department
        if department_name.lower() == "unassigned":
            department_filter = Q(department__isnull=True) | Q(department="")
        else:
            department_filter = Q(department=department_name)

        # Get pagination parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get bills for department
        bills = (
            Bill.objects.filter(company=company)
            .filter(department_filter)
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
