from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.serializers.invoice import InvoiceSerializer, InvoiceCreateSerializer
from financial.views.api.ar_aging import get_company_from_request


class InvoiceListCreateView(generics.ListCreateAPIView):
    """
    List all invoices for a company or create a new invoice.
    GET: Returns list of invoices filtered by company
    POST: Creates a new invoice for the company
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for list vs create"""
        if self.request.method == 'POST':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def get_queryset(self):
        """Filter invoices by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Invoice.objects.none()
        
        queryset = Invoice.objects.filter(company=company)
        
        # Optional filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        customer_name = self.request.query_params.get("customer_name")
        if customer_name:
            queryset = queryset.filter(customer_name__icontains=customer_name)
        
        invoice_number = self.request.query_params.get("invoice_number")
        if invoice_number:
            queryset = queryset.filter(invoice_number__icontains=invoice_number)
        
        return queryset.order_by("-invoice_date")

    def perform_create(self, serializer):
        """Create invoice with company and user info"""
        company = get_company_from_request(self.request)
        if not company:
            raise ValidationError({
                "company": "Company is required. Please provide company_id in query params or ensure you own a company."
            })
        
        # Check if invoice_number already exists for this company
        invoice_number = serializer.validated_data.get('invoice_number')
        if Invoice.objects.filter(company=company, invoice_number=invoice_number).exists():
            raise ValidationError({
                "invoice_number": f"Invoice number '{invoice_number}' already exists for this company."
            })
        
        invoice = serializer.save(
            company=company,
            created_by=self.request.user,
            updated_by=self.request.user
        )
        
        # Log audit trail if available
        try:
            from financial.models.audit_trail import AuditTrail
            AuditTrail.log_action(
                action="create",
                entity_type="invoice",
                entity_id=invoice.id,
                reference=invoice.invoice_number,
                details=f"Invoice {invoice.invoice_number} created for {invoice.customer_name}",
                company=company,
                user=self.request.user if self.request.user.is_authenticated else None,
                changes={"invoice_number": invoice_number, "total_amount": str(invoice.total_amount)},
            )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass


class InvoiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete an invoice.
    GET: Returns invoice details
    PUT/PATCH: Updates invoice
    DELETE: Deletes invoice
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Filter invoices by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Invoice.objects.none()
        
        return Invoice.objects.filter(company=company)

    def update(self, request, *args, **kwargs):
        """Update invoice with validation"""
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        
        # Get company for validation
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company is required. Please provide company_id in query params."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check invoice_number uniqueness if being updated
        invoice_number = request.data.get('invoice_number')
        if invoice_number and invoice_number != instance.invoice_number:
            if Invoice.objects.filter(company=company, invoice_number=invoice_number).exists():
                return Response(
                    {"invoice_number": f"Invoice number '{invoice_number}' already exists for this company."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Track changes for audit trail
        old_data = {
            "invoice_number": instance.invoice_number,
            "total_amount": str(instance.total_amount),
            "paid_amount": str(instance.paid_amount),
            "status": instance.status,
        }
        
        self.perform_update(serializer)
        
        # Log audit trail
        try:
            from financial.models.audit_trail import AuditTrail
            updated_instance = self.get_object()
            new_data = {
                "invoice_number": updated_instance.invoice_number,
                "total_amount": str(updated_instance.total_amount),
                "paid_amount": str(updated_instance.paid_amount),
                "status": updated_instance.status,
            }
            changes = {k: f"{old_data[k]} -> {new_data[k]}" for k in old_data if old_data[k] != new_data[k]}
            
            if changes:
                AuditTrail.log_action(
                    action="update",
                    entity_type="invoice",
                    entity_id=updated_instance.id,
                    reference=updated_instance.invoice_number,
                    details=f"Invoice {updated_instance.invoice_number} updated",
                    company=company,
                    user=request.user if request.user.is_authenticated else None,
                    changes=changes,
                )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass
        
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Update invoice with user info"""
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Delete invoice with audit trail"""
        instance = self.get_object()
        company = get_company_from_request(request)
        
        # Log audit trail before deletion
        try:
            from financial.models.audit_trail import AuditTrail
            AuditTrail.log_action(
                action="delete",
                entity_type="invoice",
                entity_id=instance.id,
                reference=instance.invoice_number,
                details=f"Invoice {instance.invoice_number} deleted",
                company=company,
                user=request.user if request.user.is_authenticated else None,
                changes={"status": "deleted"},
            )
        except Exception:
            # Audit trail is optional, continue if it fails
            pass
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

