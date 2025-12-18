from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
from calendar import monthrange

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.models.budget import ExpenseBudget, BudgetPeriodTypeChoices
from expense.serializers.budget import (
    ExpenseBudgetSerializer,
    ExpenseBudgetCreateSerializer,
    ExpenseBudgetChoicesSerializer,
)
from expense.views.api.bills import get_company_from_request
from financial.enums import BillsStatusChoices


class BudgetManagementView(APIView):
    """
    Combined API endpoint for Budget Management.

    GET /api/expense/budget/
    - Returns all budget dashboard data:
      * KPIs: Total Budget, Total Actual, Over Budget count, Under Budget count
      * Budget vs Actual by Category: Chart data
      * Budget Details: Category-wise breakdown table
    - Query parameters:
      * period_start (optional): Start date for filtering (YYYY-MM-DD)
      * period_end (optional): End date for filtering (YYYY-MM-DD)
      * If not provided, uses current month

    POST /api/expense/budget/
    - Create a new budget entry
    - Required fields: category, period_type, period, budget_amount
    - Optional fields: department, notes
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in Indian numbering system"""
        if amount == 0:
            return "₹0"
        if amount >= 10000000:
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"
        elif amount >= 100000:
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:
            return f"₹{amount:,.2f}"

    @staticmethod
    def _format_amount_indian(amount: Decimal) -> str:
        """Format amount with Indian numbering (with commas)"""
        if amount == 0:
            return "₹0"
        # Format with Indian numbering: ₹2,26,35,558
        amount_str = f"{amount:,.2f}"
        parts = amount_str.split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"

        # Add commas in Indian style (last 3 digits, then groups of 2)
        if len(integer_part) <= 3:
            formatted = integer_part
        else:
            formatted = integer_part[:-3] + "," + integer_part[-3:]
            # Add more commas for larger numbers
            if len(integer_part) > 5:
                remaining = integer_part[:-5]
                if len(remaining) > 2:
                    formatted = (
                        remaining[:-2] + "," + remaining[-2:] + "," + integer_part[-5:]
                    )
                else:
                    formatted = remaining + "," + integer_part[-5:]

        return f"₹{formatted}.{decimal_part}"

    def get(self, request, *args, **kwargs):
        """Get all budget dashboard data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "kpis": {
                        "total_budget": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "categories_count": 0,
                        },
                        "total_actual": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "utilization_percentage": 0.0,
                        },
                        "over_budget": {
                            "count": 0,
                            "description": "Categories exceeding budget",
                        },
                        "under_budget": {
                            "count": 0,
                            "description": "Categories within budget",
                        },
                    },
                    "budget_vs_actual_chart": [],
                    "budget_details": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get query parameters for period filtering
        today = timezone.now().date()
        period_start_str = request.query_params.get("period_start")
        period_end_str = request.query_params.get("period_end")

        if period_start_str and period_end_str:
            try:
                period_start = datetime.strptime(period_start_str, "%Y-%m-%d").date()
                period_end = datetime.strptime(period_end_str, "%Y-%m-%d").date()
            except ValueError:
                # Default to current month
                period_start = today.replace(day=1)
                last_day = monthrange(today.year, today.month)[1]
                period_end = today.replace(day=last_day)
        else:
            # Default to current month
            period_start = today.replace(day=1)
            last_day = monthrange(today.year, today.month)[1]
            period_end = today.replace(day=last_day)

        # Get all budgets that overlap with the period
        budgets = ExpenseBudget.objects.filter(
            company=company,
            period__lte=period_end,
        ).filter(
            Q(period__gte=period_start)
            | Q(
                period__lte=period_start,
                period__gte=period_start - timedelta(days=365),
            )
        )

        # Get all bills for actual calculation
        bills = (
            Bill.objects.filter(
                company=company,
                bill_date__gte=period_start,
                bill_date__lte=period_end,
            )
            .exclude(status=BillsStatusChoices.CANCELLED)
            .exclude(category="")
            .exclude(category__isnull=True)
        )

        # Calculate KPIs
        total_budget = sum(budget.budget_amount for budget in budgets)
        total_actual = Decimal("0")
        over_budget_count = 0
        under_budget_count = 0

        # Group budgets by category for calculation
        category_budgets = defaultdict(
            lambda: {"budget": Decimal("0"), "actual": Decimal("0")}
        )

        for budget in budgets:
            period_start_budget = budget.get_period_start()
            period_end_budget = budget.get_period_end()

            # Use the intersection of budget period and requested period
            actual_period_start = max(period_start, period_start_budget)
            actual_period_end = min(period_end, period_end_budget)

            if actual_period_start <= actual_period_end:
                actual = budget.calculate_actual_amount(
                    actual_period_start, actual_period_end
                )
                total_actual += actual

                category_key = budget.category
                category_budgets[category_key]["budget"] += budget.budget_amount
                category_budgets[category_key]["actual"] += actual

                # Check status
                utilization = budget.get_utilization_percentage(
                    actual_period_start, actual_period_end
                )
                if utilization >= 100:
                    over_budget_count += 1
                else:
                    under_budget_count += 1

        # Also calculate actuals for categories that have bills but no budgets
        for bill in bills:
            category = bill.category
            if category not in category_budgets:
                category_budgets[category] = {
                    "budget": Decimal("0"),
                    "actual": Decimal("0"),
                }
            category_budgets[category]["actual"] += bill.total

        utilization_percentage = (
            float((total_actual / total_budget) * 100) if total_budget > 0 else 0.0
        )

        # Get unique categories count
        categories_count = len(set(budget.category for budget in budgets))

        # Budget vs Actual by Category Chart
        budget_vs_actual_chart = []
        for category, data in sorted(
            category_budgets.items(), key=lambda x: x[1]["budget"], reverse=True
        ):
            budget_vs_actual_chart.append(
                {
                    "category": category,
                    "budget": {
                        "amount": float(data["budget"]),
                        "amount_display": self._format_amount(data["budget"]),
                    },
                    "actual": {
                        "amount": float(data["actual"]),
                        "amount_display": self._format_amount(data["actual"]),
                    },
                }
            )

        # Budget Details Table
        budget_details = []
        for budget in budgets:
            period_start_budget = budget.get_period_start()
            period_end_budget = budget.get_period_end()

            # Use the intersection of budget period and requested period
            actual_period_start = max(period_start, period_start_budget)
            actual_period_end = min(period_end, period_end_budget)

            if actual_period_start <= actual_period_end:
                actual = budget.calculate_actual_amount(
                    actual_period_start, actual_period_end
                )
                variance = budget.get_variance(actual_period_start, actual_period_end)
                utilization = budget.get_utilization_percentage(
                    actual_period_start, actual_period_end
                )
                status_value = budget.get_status(actual_period_start, actual_period_end)

                budget_details.append(
                    {
                        "id": str(budget.id),
                        "category": budget.category,
                        "department": budget.department or "-",
                        "budget": {
                            "amount": float(budget.budget_amount),
                            "amount_display": self._format_amount_indian(
                                budget.budget_amount
                            ),
                        },
                        "actual": {
                            "amount": float(actual),
                            "amount_display": self._format_amount_indian(actual),
                        },
                        "variance": {
                            "amount": float(variance),
                            "amount_display": self._format_amount_indian(abs(variance)),
                            "is_negative": variance < 0,
                        },
                        "utilization": {
                            "percentage": round(utilization, 1),
                            "display": f"{round(utilization, 1)}%",
                        },
                        "status": status_value,
                    }
                )

        # Sort budget details by category
        budget_details.sort(key=lambda x: x["category"])

        kpis = {
            "total_budget": {
                "amount": float(total_budget),
                "amount_display": self._format_amount_indian(total_budget),
                "categories_count": categories_count,
            },
            "total_actual": {
                "amount": float(total_actual),
                "amount_display": self._format_amount_indian(total_actual),
                "utilization_percentage": round(utilization_percentage, 1),
            },
            "over_budget": {
                "count": over_budget_count,
                "description": "Categories exceeding budget",
            },
            "under_budget": {
                "count": under_budget_count,
                "description": "Categories within budget",
            },
        }

        return Response(
            {
                "kpis": kpis,
                "budget_vs_actual_chart": budget_vs_actual_chart,
                "budget_details": budget_details,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        """Create a new budget entry"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseBudgetCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            budget = serializer.save()
            response_serializer = ExpenseBudgetSerializer(budget)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BudgetRetrieveUpdateDestroyView(APIView):
    """
    Retrieve, Update, Delete budget entry.

    GET /api/expense/budget/<uuid:id>/
    PUT /api/expense/budget/<uuid:id>/
    PATCH /api/expense/budget/<uuid:id>/
    DELETE /api/expense/budget/<uuid:id>/
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, id, company):
        """Get budget object"""
        try:
            return ExpenseBudget.objects.get(id=id, company=company)
        except ExpenseBudget.DoesNotExist:
            return None

    def get(self, request, id, *args, **kwargs):
        """Retrieve budget entry"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        budget = self.get_object(id, company)
        if not budget:
            return Response(
                {"error": "Budget not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseBudgetSerializer(budget)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id, *args, **kwargs):
        """Update budget entry (full update)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        budget = self.get_object(id, company)
        if not budget:
            return Response(
                {"error": "Budget not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseBudgetCreateSerializer(
            budget, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            response_serializer = ExpenseBudgetSerializer(budget)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id, *args, **kwargs):
        """Update budget entry (partial update)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        budget = self.get_object(id, company)
        if not budget:
            return Response(
                {"error": "Budget not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseBudgetCreateSerializer(
            budget, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            response_serializer = ExpenseBudgetSerializer(budget)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, *args, **kwargs):
        """Delete budget entry"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        budget = self.get_object(id, company)
        if not budget:
            return Response(
                {"error": "Budget not found"}, status=status.HTTP_404_NOT_FOUND
            )

        budget.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BudgetChoicesView(APIView):
    """
    Get choices for budget form dropdowns.

    GET /api/expense/budget/choices/
    - Returns: categories, departments, period_types
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Get budget form choices"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "categories": [],
                    "departments": [],
                    "period_types": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get categories from bills
        categories = (
            Bill.objects.filter(company=company)
            .exclude(category="")
            .exclude(category__isnull=True)
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )

        # Get departments from bills
        departments = (
            Bill.objects.filter(company=company)
            .exclude(department="")
            .exclude(department__isnull=True)
            .values_list("department", flat=True)
            .distinct()
            .order_by("department")
        )

        # Period types
        period_types = [
            {"value": choice[0], "label": choice[1]}
            for choice in BudgetPeriodTypeChoices.choices
        ]

        data = {
            "categories": list(categories),
            "departments": list(departments),
            "period_types": period_types,
        }

        serializer = ExpenseBudgetChoicesSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
