from decimal import Decimal
from django.db.models import Q
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from accounts.models import Company
from accounts.utils import get_user_company
from expense.models.bills import Bill
from expense.serializers.bills import (
    BillSerializer,
    BillCreateSerializer,
)
from financial.enums import BillsStatusChoices


def get_company_from_request(request):
    """Helper function to get company from request"""
    # First try: request.company (set by middleware)
    company = getattr(request, "company", None)
    if company:
        return company

    # Second try: get from user
    if request.user.is_authenticated:
        company = get_user_company(request.user)
        if company:
            return company

    # Third try: query parameter
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return None

    return None


class BillListCreateView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating bills.

    GET /api/expense/bills/
    - List all bills for the company
    - Query parameters:
      * company_id (optional): Company UUID
      * status (optional): Filter by status (PENDING, PARTIAL, PAID, OVERDUE, CANCELLED)
      * vendor_name (optional): Filter by vendor name (partial match)
      * bill_number (optional): Filter by bill number (partial match)
      * search (optional): Search across bill_number, vendor_name, category
      * category (optional): Filter by category

    POST /api/expense/bills/
    - Create a new bill
    - Automatically creates/updates vendor if needed
    - Calculates GST and TDS amounts automatically
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter bills by company and optional filters"""
        company = get_company_from_request(self.request)
        if not company:
            return Bill.objects.none()

        queryset = Bill.objects.filter(company=company).select_related("vendor")

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by vendor name
        vendor_name = self.request.query_params.get("vendor_name")
        if vendor_name:
            queryset = queryset.filter(
                Q(vendor__name__icontains=vendor_name)
                | Q(vendor_name__icontains=vendor_name)
            )

        # Filter by bill number
        bill_number = self.request.query_params.get("bill_number")
        if bill_number:
            queryset = queryset.filter(bill_number__icontains=bill_number)

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__icontains=category)

        # Search across multiple fields
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(bill_number__icontains=search)
                | Q(vendor__name__icontains=search)
                | Q(vendor_name__icontains=search)
                | Q(category__icontains=search)
                | Q(item_name__icontains=search)
            )

        return queryset.order_by("-bill_date", "-created_at")

    def get_serializer_class(self):
        """Use create serializer for POST, list serializer for GET"""
        if self.request.method == "POST":
            return BillCreateSerializer
        return BillSerializer

    def perform_create(self, serializer):
        """Set company and user when creating bill"""
        company = get_company_from_request(self.request)
        if not company:
            raise ValidationError({"error": "Company not found"})

        serializer.save(company=company, user=self.request.user)

    def list(self, request, *args, **kwargs):
        """List bills with pagination"""
        queryset = self.filter_queryset(self.get_queryset())

        # Get pagination parameters
        page_size = request.query_params.get("page_size", 50)
        page = request.query_params.get("page", 1)

        try:
            page_size = int(page_size)
            page = int(page)
        except (ValueError, TypeError):
            page_size = 50
            page = 1

        # Calculate pagination
        start = (page - 1) * page_size
        end = start + page_size

        total_count = queryset.count()
        bills = queryset[start:end]

        serializer = self.get_serializer(bills, many=True)

        return Response(
            {
                "count": total_count,
                "next": f"?page={page + 1}" if end < total_count else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": serializer.data,
            }
        )


class BillRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting a specific bill.

    GET /api/expense/bills/<uuid:id>/
    - Retrieve bill details

    PUT /api/expense/bills/<uuid:id>/
    - Full update of bill

    PATCH /api/expense/bills/<uuid:id>/
    - Partial update of bill

    DELETE /api/expense/bills/<uuid:id>/
    - Delete bill (soft delete by setting status to CANCELLED)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BillSerializer

    def get_queryset(self):
        """Filter bills by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Bill.objects.none()
        return Bill.objects.filter(company=company).select_related("vendor")

    def perform_update(self, serializer):
        """Set updated_by when updating bill"""
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete by setting status to CANCELLED"""
        instance.status = BillsStatusChoices.CANCELLED
        instance.updated_by = self.request.user
        instance.save()
