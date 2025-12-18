from decimal import Decimal
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from accounts.models import Company
from expense.models.recurring import (
    RecurringExpense,
    RecurringExpenseFrequencyChoices,
    RecurringExpenseStatusChoices,
)
from expense.serializers.recurring import (
    RecurringExpenseSerializer,
    RecurringExpenseCreateSerializer,
)
from expense.views.api.bills import get_company_from_request


class RecurringExpensePagination(PageNumberPagination):
    """Pagination for recurring expenses list"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class RecurringExpenseListCreateView(APIView):
    """
    Combined API endpoint for recurring expenses (Summary + List).

    GET /api/expense/recurring/
    - Returns:
      * summary: KPIs (active_subscriptions, monthly_commitment, due_soon_7d, upcoming_renewals)
      * results: List of recurring expenses with pagination
    - Query parameters:
      * search (optional): Search by vendor, category, frequency, name
      * status (optional): Filter by status (Active, Expired, Cancelled, Paused)
      * frequency (optional): Filter by frequency (Monthly, Quarterly, Semi-annual, Annual)
      * category (optional): Filter by category
      * page (optional): Page number
      * page_size (optional): Items per page

    POST /api/expense/recurring/
    - Create a new recurring expense
    """

    permission_classes = [IsAuthenticated]
    pagination_class = RecurringExpensePagination

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores with Indian numbering"""
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

    def _calculate_summary(self, company):
        """Calculate summary/KPIs for recurring expenses"""
        if not company:
            return {
                "active_subscriptions": 0,
                "monthly_commitment": {
                    "amount": 0,
                    "amount_display": "₹0",
                },
                "due_soon_7d": 0,
                "upcoming_renewals": 0,
            }

        # Get all recurring expenses
        recurring_expenses = RecurringExpense.objects.filter(company=company)

        # Active subscriptions
        active_subscriptions = recurring_expenses.filter(
            status=RecurringExpenseStatusChoices.ACTIVE
        ).count()

        # Monthly commitment - calculate based on frequency
        monthly_commitment = Decimal("0")
        for expense in recurring_expenses.filter(
            status=RecurringExpenseStatusChoices.ACTIVE
        ):
            total_amount = expense.get_total_amount()
            if expense.frequency == RecurringExpenseFrequencyChoices.MONTHLY:
                monthly_commitment += total_amount
            elif expense.frequency == RecurringExpenseFrequencyChoices.QUARTERLY:
                monthly_commitment += total_amount / Decimal("3")
            elif expense.frequency == RecurringExpenseFrequencyChoices.SEMI_ANNUAL:
                monthly_commitment += total_amount / Decimal("6")
            elif expense.frequency == RecurringExpenseFrequencyChoices.ANNUAL:
                monthly_commitment += total_amount / Decimal("12")

        # Due soon (within 7 days)
        due_soon_7d = sum(
            1
            for expense in recurring_expenses.filter(
                status=RecurringExpenseStatusChoices.ACTIVE
            )
            if expense.is_due_soon(days=7)
        )

        # Upcoming renewals (within renewal_reminder_days, default 30)
        today = timezone.now().date()
        upcoming_renewals = 0
        for expense in recurring_expenses.filter(
            status=RecurringExpenseStatusChoices.ACTIVE
        ):
            if expense.end_date:
                days_until_renewal = (expense.end_date - today).days
                if 0 <= days_until_renewal <= expense.renewal_reminder_days:
                    upcoming_renewals += 1

        return {
            "active_subscriptions": active_subscriptions,
            "monthly_commitment": {
                "amount": float(monthly_commitment),
                "amount_display": self._format_amount(monthly_commitment),
            },
            "due_soon_7d": due_soon_7d,
            "upcoming_renewals": upcoming_renewals,
        }

    def get(self, request, *args, **kwargs):
        """Get summary and list of recurring expenses"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "summary": {
                        "active_subscriptions": 0,
                        "monthly_commitment": {
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "due_soon_7d": 0,
                        "upcoming_renewals": 0,
                    },
                    "count": 0,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        # Calculate summary
        summary = self._calculate_summary(company)

        # Get queryset for list
        queryset = RecurringExpense.objects.filter(company=company).select_related(
            "vendor"
        )

        # Apply filters
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(vendor_name__icontains=search)
                | Q(category__icontains=search)
                | Q(sub_category__icontains=search)
                | Q(frequency__icontains=search)
                | Q(description__icontains=search)
            )

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        frequency_filter = request.query_params.get("frequency")
        if frequency_filter:
            queryset = queryset.filter(frequency=frequency_filter)

        category_filter = request.query_params.get("category")
        if category_filter:
            queryset = queryset.filter(category__icontains=category_filter)

        # Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = RecurringExpenseSerializer(page, many=True)
            paginated_response = paginator.get_paginated_response(serializer.data)
            # Add summary to paginated response
            paginated_response.data["summary"] = summary
            return paginated_response

        serializer = RecurringExpenseSerializer(queryset, many=True)
        return Response(
            {
                "summary": summary,
                "count": len(serializer.data),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        """Create a new recurring expense"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecurringExpenseCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            recurring_expense = serializer.save()
            response_serializer = RecurringExpenseSerializer(recurring_expense)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecurringExpenseRetrieveUpdateDestroyView(APIView):
    """
    Retrieve, update, or delete a recurring expense.

    GET /api/expense/recurring/<uuid:id>/
    PUT /api/expense/recurring/<uuid:id>/
    PATCH /api/expense/recurring/<uuid:id>/
    DELETE /api/expense/recurring/<uuid:id>/
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, id, company):
        """Get recurring expense object"""
        try:
            return RecurringExpense.objects.get(id=id, company=company)
        except RecurringExpense.DoesNotExist:
            return None

    def get(self, request, id, *args, **kwargs):
        """Get recurring expense details"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recurring_expense = self.get_object(id, company)
        if not recurring_expense:
            return Response(
                {"detail": "Recurring expense not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RecurringExpenseSerializer(recurring_expense)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id, *args, **kwargs):
        """Update recurring expense (full update)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recurring_expense = self.get_object(id, company)
        if not recurring_expense:
            return Response(
                {"detail": "Recurring expense not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RecurringExpenseCreateSerializer(
            recurring_expense, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            recurring_expense = serializer.save()
            response_serializer = RecurringExpenseSerializer(recurring_expense)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id, *args, **kwargs):
        """Update recurring expense (partial update)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recurring_expense = self.get_object(id, company)
        if not recurring_expense:
            return Response(
                {"detail": "Recurring expense not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RecurringExpenseCreateSerializer(
            recurring_expense,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            recurring_expense = serializer.save()
            response_serializer = RecurringExpenseSerializer(recurring_expense)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, *args, **kwargs):
        """Delete recurring expense"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recurring_expense = self.get_object(id, company)
        if not recurring_expense:
            return Response(
                {"detail": "Recurring expense not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        recurring_expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecurringExpenseChoicesView(APIView):
    """
    Get dropdown choices for recurring expenses.

    GET /api/expense/recurring/choices/
    - Returns:
      * frequency_choices: Available frequency options
      * status_choices: Available status options
      * categories: Available categories from existing bills and recurring expenses
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Get dropdown choices"""
        company = get_company_from_request(request)

        frequency_choices = [
            {"value": choice[0], "label": choice[1]}
            for choice in RecurringExpenseFrequencyChoices.choices
        ]

        status_choices = [
            {"value": choice[0], "label": choice[1]}
            for choice in RecurringExpenseStatusChoices.choices
        ]

        # Get unique categories from bills and recurring expenses
        categories = set()
        if company:
            from expense.models.bills import Bill
            from financial.enums import BillsStatusChoices

            # Get categories from bills
            bill_categories = (
                Bill.objects.filter(company=company)
                .exclude(status=BillsStatusChoices.CANCELLED)
                .exclude(category="")
                .exclude(category__isnull=True)
                .values_list("category", flat=True)
                .distinct()
            )
            categories.update(bill_categories)

            # Get categories from recurring expenses
            recurring_categories = (
                RecurringExpense.objects.filter(company=company)
                .exclude(category="")
                .exclude(category__isnull=True)
                .values_list("category", flat=True)
                .distinct()
            )
            categories.update(recurring_categories)

        category_choices = sorted([{"value": cat, "label": cat} for cat in categories])

        return Response(
            {
                "frequency_choices": frequency_choices,
                "status_choices": status_choices,
                "categories": category_choices,
            },
            status=status.HTTP_200_OK,
        )
