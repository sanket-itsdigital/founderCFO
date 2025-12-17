from decimal import Decimal
from collections import defaultdict
from django.db.models import Q, Count, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.views.api.bills import get_company_from_request
from expense.serializers.bills import BillSerializer
from financial.enums import BillsStatusChoices


class CategoriesView(APIView):
    """
    Combined API endpoint for all category-related data.

    GET /api/expense/categories/
    - Returns:
      * Summary KPIs: TDS Applicable Expenses, GST Input Tax Credit
      * Category Distribution (for donut chart)
      * Top Sub-Categories (for bar chart)
      * All Categories list with detailed information
    - Query parameters:
      * search (optional): Search categories by name
      * top_subcategories_limit (optional): Number of top sub-categories to return (default: 10)
      * page (optional): Page number for all categories list (default: 1)
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
        """Get all category data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "tds_applicable_expenses": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "transaction_count": 0,
                        },
                        "gst_input_tax_credit": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "transaction_count": 0,
                        },
                    },
                    "category_distribution": [],
                    "top_subcategories": [],
                    "all_categories": {
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
        top_subcategories_limit = int(
            request.query_params.get("top_subcategories_limit", 10)
        )
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get all bills (excluding cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Apply search filter if provided (for all_categories only)
        bills_for_all = bills
        if search:
            bills_for_all = bills.filter(category__icontains=search)

        # Calculate TDS Applicable Expenses
        tds_bills = bills.filter(tds_percentage__gt=0)
        tds_total = sum(bill.total for bill in tds_bills)
        tds_transaction_count = tds_bills.count()

        # Calculate GST Input Tax Credit (ITC)
        # ITC is eligible when GST is paid (CGST + SGST + IGST > 0)
        itc_bills = bills.filter(
            Q(cgst_percentage__gt=0)
            | Q(sgst_percentage__gt=0)
            | Q(igst_percentage__gt=0)
        )
        itc_total = sum(
            bill.cgst_amount + bill.sgst_amount + bill.igst_amount for bill in itc_bills
        )
        itc_transaction_count = itc_bills.count()

        summary = {
            "tds_applicable_expenses": {
                "amount": float(tds_total),
                "amount_display": self._format_amount(tds_total),
                "transaction_count": tds_transaction_count,
            },
            "gst_input_tax_credit": {
                "amount": float(itc_total),
                "amount_display": self._format_amount(itc_total),
                "transaction_count": itc_transaction_count,
            },
        }

        # Group by category for distribution and all categories
        category_data = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "description": "",
                "subcategories": defaultdict(lambda: Decimal("0")),
            }
        )

        # Category descriptions mapping
        category_descriptions = {
            "Technology": "Software, cloud, and IT infrastructure",
            "Technology & Infrastructure": "Software, cloud, and IT infrastructure",
            "Personnel": "Employee salaries, benefits, and related expenses",
            "Personnel Expenses": "Employee salaries, benefits, and related expenses",
            "Marketing": "Advertising, marketing, and sales expenses",
            "Marketing & Sales": "Advertising, marketing, and sales expenses",
            "Establishment": "Office rent, utilities, and facilities",
            "Establishment Expenses": "Office rent, utilities, and facilities",
            "Travel": "Business travel and transport expenses",
            "Travel & Conveyance": "Business travel and transport expenses",
            "Professional Fees": "Professional services and legal fees",
            "Prof. Fees": "Professional services and legal fees",
            "Financial": "Banking and financial charges",
            "Financial Expenses": "Banking and financial charges",
            "Depreciation": "Asset depreciation and amortization",
            "Depreciation & Amortization": "Asset depreciation and amortization",
            "Administration": "Administrative and operational expenses",
            "Statutory": "Government taxes and statutory payments",
            "Miscellaneous": "Other operational expenses",
        }

        for bill in bills:
            category = bill.category or "Uncategorized"
            category_data[category]["total_spend"] += bill.total
            category_data[category]["bill_count"] += 1
            if not category_data[category]["description"]:
                category_data[category]["description"] = category_descriptions.get(
                    category, f"{category} related expenses"
                )
            # Track sub-categories (using item_name as sub-category)
            if bill.item_name:
                category_data[category]["subcategories"][bill.item_name] += bill.total

        total_spend_all = sum(data["total_spend"] for data in category_data.values())

        # Category Distribution (for donut chart)
        category_distribution = []
        for category, data in sorted(
            category_data.items(), key=lambda x: x[1]["total_spend"], reverse=True
        ):
            percentage = (
                float((data["total_spend"] / total_spend_all) * 100)
                if total_spend_all > 0
                else 0.0
            )
            category_distribution.append(
                {
                    "category": category,
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "percentage": round(percentage, 1),
                    "bill_count": data["bill_count"],
                }
            )

        # Top Sub-Categories (for bar chart)
        all_subcategories = defaultdict(lambda: Decimal("0"))
        for category, data in category_data.items():
            for subcategory, amount in data["subcategories"].items():
                all_subcategories[subcategory] += amount

        sorted_subcategories = sorted(
            all_subcategories.items(), key=lambda x: x[1], reverse=True
        )[:top_subcategories_limit]

        top_subcategories = []
        for subcategory, amount in sorted_subcategories:
            top_subcategories.append(
                {
                    "subcategory_name": subcategory,
                    "total_spend": float(amount),
                    "total_spend_display": self._format_amount(amount),
                }
            )

        # All Categories (for table) - with search filter applied
        category_data_all = defaultdict(
            lambda: {
                "total_spend": Decimal("0"),
                "bill_count": 0,
                "description": "",
            }
        )

        for bill in bills_for_all:
            category = bill.category or "Uncategorized"
            category_data_all[category]["total_spend"] += bill.total
            category_data_all[category]["bill_count"] += 1
            if not category_data_all[category]["description"]:
                category_data_all[category]["description"] = category_descriptions.get(
                    category, f"{category} related expenses"
                )

        total_spend_all_filtered = sum(
            data["total_spend"] for data in category_data_all.values()
        )

        # Convert to list and calculate percentages
        categories_list = []
        for category, data in category_data_all.items():
            percentage = (
                float((data["total_spend"] / total_spend_all_filtered) * 100)
                if total_spend_all_filtered > 0
                else 0.0
            )

            categories_list.append(
                {
                    "category": category,
                    "description": data["description"],
                    "total_spend": float(data["total_spend"]),
                    "total_spend_display": self._format_amount(data["total_spend"]),
                    "bills_count": data["bill_count"],
                    "percentage_of_total": round(percentage, 1),
                }
            )

        # Sort by total spend descending
        categories_list.sort(key=lambda x: x["total_spend"], reverse=True)

        # Pagination
        total_count = len(categories_list)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_categories = categories_list[start:end]

        all_categories = {
            "count": total_count,
            "results": paginated_categories,
            "total_spend": float(total_spend_all_filtered),
            "total_spend_display": self._format_amount(total_spend_all_filtered),
            "page": page,
            "page_size": page_size,
            "next": f"?page={page + 1}" if end < total_count else None,
            "previous": f"?page={page - 1}" if page > 1 else None,
        }

        return Response(
            {
                "summary": summary,
                "category_distribution": category_distribution,
                "top_subcategories": top_subcategories,
                "all_categories": all_categories,
            },
            status=status.HTTP_200_OK,
        )


class CategoryBillsView(APIView):
    """
    API endpoint for bills of a specific category.

    GET /api/expense/categories/<category_name>/bills/
    - Returns all bills for a specific category
    - Query parameters:
      * page (optional): Page number (default: 1)
      * page_size (optional): Items per page (default: 50)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, category_name=None, *args, **kwargs):
        """Get bills for a specific category"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "count": 0,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        if not category_name:
            return Response(
                {"error": "Category name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get pagination parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        # Get bills for category
        bills = (
            Bill.objects.filter(company=company, category=category_name)
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
