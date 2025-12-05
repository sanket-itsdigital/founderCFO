from django.db import models
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Company
from financial.models.account_payable.bills import Bill
from financial.serializers.account_payable.bills import (
    BillSerializer,
    BillCreateSerializer,
    BillUpdateSerializer,
)


def get_company_from_request(request):
    """Helper function to get company from request"""
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return None
    # Try to get the first company owned by the user
    return Company.objects.filter(owner=request.user).first()


class BillListCreateView(generics.ListCreateAPIView):
    """
    List all bills for a company or create a new bill.
    GET: Returns list of bills filtered by company
    POST: Creates a new bill for the company
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for list vs create"""
        if self.request.method == 'POST':
            return BillCreateSerializer
        return BillSerializer

    def get_queryset(self):
        """Filter bills by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Bill.objects.none()
        
        queryset = Bill.objects.filter(company=company).select_related("vendor")
        
        # Optional filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        vendor_name = self.request.query_params.get("vendor_name")
        if vendor_name:
            queryset = queryset.filter(
                models.Q(vendor__name__icontains=vendor_name) |
                models.Q(vendor_name__icontains=vendor_name)
            )
        
        bill_number = self.request.query_params.get("bill_number")
        if bill_number:
            queryset = queryset.filter(bill_number__icontains=bill_number)
        
        # Search filter
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(bill_number__icontains=search) |
                models.Q(vendor__name__icontains=search) |
                models.Q(vendor_name__icontains=search) |
                models.Q(category__icontains=search)
            )
        
        return queryset.order_by("-bill_date")

    def perform_create(self, serializer):
        """Create bill with company and user info"""
        company = get_company_from_request(self.request)
        if not company:
            raise ValidationError({
                "company": "Company is required. Please provide company_id in query params or ensure you own a company."
            })
        
        # Check if bill_number already exists for this company
        bill_number = serializer.validated_data.get('bill_number')
        if Bill.objects.filter(company=company, bill_number=bill_number).exists():
            raise ValidationError({
                "bill_number": f"Bill number '{bill_number}' already exists for this company."
            })
        
        bill = serializer.save(
            company=company,
            created_by=self.request.user,
            updated_by=self.request.user
        )
        
        # Log audit trail if available
        try:
            from financial.models.account_receivable.audit_trail import AuditTrail
            AuditTrail.log_action(
                action="create",
                entity_type="bill",
                entity_id=bill.id,
                reference=bill.bill_number,
                details=f"Bill {bill.bill_number} created for {bill.get_vendor_name()}",
                company=company,
                user=self.request.user if self.request.user.is_authenticated else None,
                changes={"bill_number": bill_number, "amount": str(bill.amount)},
            )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass


class BillRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a bill.
    GET: Returns bill details
    PUT/PATCH: Updates bill
    DELETE: Deletes bill
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BillSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        """Use different serializers for update vs retrieve"""
        if self.request.method in ['PUT', 'PATCH']:
            return BillUpdateSerializer
        return BillSerializer

    def get_queryset(self):
        """Filter bills by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Bill.objects.none()
        return Bill.objects.filter(company=company).select_related("vendor")

    def perform_update(self, serializer):
        """Update bill with user info"""
        serializer.save(updated_by=self.request.user)
        
        # Log audit trail if available
        try:
            bill = serializer.instance
            from financial.models.account_receivable.audit_trail import AuditTrail
            AuditTrail.log_action(
                action="update",
                entity_type="bill",
                entity_id=bill.id,
                reference=bill.bill_number,
                details=f"Bill {bill.bill_number} updated",
                company=bill.company,
                user=self.request.user if self.request.user.is_authenticated else None,
                changes=serializer.validated_data,
            )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass

    def perform_destroy(self, instance):
        """Delete bill and log audit trail"""
        bill_number = instance.bill_number
        company = instance.company
        
        instance.delete()
        
        # Log audit trail if available
        try:
            from financial.models.account_receivable.audit_trail import AuditTrail
            AuditTrail.log_action(
                action="delete",
                entity_type="bill",
                entity_id=str(instance.id),
                reference=bill_number,
                details=f"Bill {bill_number} deleted",
                company=company,
                user=self.request.user if self.request.user.is_authenticated else None,
            )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass

