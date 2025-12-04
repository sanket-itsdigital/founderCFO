from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, F, Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.write_offs import WriteOff
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.account_receivable.write_offs import WriteOffCandidateSerializer, WriteOffSerializer
from financial.views.api.account_receivable.ar_aging import get_company_from_request


class WriteOffsSummaryView(APIView):
    """Get write-offs summary statistics"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "write_off_candidates_count": 0,
                "potential_write_off_amount": 0,
                "selected_count": 0,
                "selected_amount": 0,
                "already_written_off_count": 0,
                "already_written_off_amount": 0,
            })

        today = timezone.now().date()
        cutoff_date = today - timedelta(days=90)

        # Write-off candidates (invoices over 90 days overdue)
        candidates = Invoice.objects.filter(
            company=company,
            due_date__lt=cutoff_date
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        ).exclude(
            write_offs__isnull=False  # Exclude already written off
        )

        candidates_count = candidates.count()
        potential_amount = candidates.aggregate(
            total=Sum(F('total_amount') - F('paid_amount'))
        )['total'] or Decimal("0.00")

        # Already written off
        written_off = WriteOff.objects.filter(company=company)
        written_off_count = written_off.count()
        written_off_amount = written_off.aggregate(
            total=Sum('write_off_amount')
        )['total'] or Decimal("0.00")

        # Selected (from request if provided)
        selected_ids = request.query_params.getlist("selected_ids", [])
        selected_count = len(selected_ids)
        selected_amount = Decimal("0.00")
        if selected_ids:
            selected_invoices = Invoice.objects.filter(
                id__in=selected_ids,
                company=company
            )
            selected_amount = sum(
                invoice.balance_amount for invoice in selected_invoices
            )

        return Response({
            "write_off_candidates_count": candidates_count,
            "potential_write_off_amount": float(potential_amount),
            "potential_write_off_amount_display": self._in_lakhs(potential_amount),
            "selected_count": selected_count,
            "selected_amount": float(selected_amount),
            "selected_amount_display": self._in_lakhs(selected_amount),
            "already_written_off_count": written_off_count,
            "already_written_off_amount": float(written_off_amount),
            "already_written_off_amount_display": self._in_lakhs(written_off_amount),
        })


class WriteOffCandidatesListView(APIView):
    """List write-off candidate invoices"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response([])

        today = timezone.now().date()
        cutoff_date = today - timedelta(days=90)

        candidates = Invoice.objects.filter(
            company=company,
            due_date__lt=cutoff_date
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        ).exclude(
            write_offs__isnull=False
        )

        candidates_data = []
        for invoice in candidates:
            days_overdue = (today - invoice.due_date).days
            balance = invoice.balance_amount
            
            candidates_data.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer_name,
                "invoice_date": invoice.invoice_date,
                "due_date": invoice.due_date,
                "amount": float(invoice.total_amount),
                "amount_display": self._format_amount(invoice.total_amount),
                "balance_due": float(balance),
                "balance_due_display": self._format_amount(balance),
                "days_overdue": days_overdue,
                "reason": "Aging > 90 days",
            })

        serializer = WriteOffCandidateSerializer(data=candidates_data, many=True)
        serializer.is_valid()
        return Response(serializer.data)

    @staticmethod
    def _format_amount(amount):
        """Format amount for display"""
        from decimal import Decimal
        if amount >= 100000:
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        elif amount >= 1000:
            thousands = amount / Decimal("1000")
            return f"₹{thousands.quantize(Decimal('0.01'))}K"
        return f"₹{amount:,.0f}"


class WriteOffListCreateView(generics.ListCreateAPIView):
    """List and create write-offs"""
    permission_classes = [IsAuthenticated]
    serializer_class = WriteOffSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return WriteOff.objects.none()
        
        return WriteOff.objects.filter(company=company).select_related('invoice').order_by('-write_off_date')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        invoice = serializer.validated_data['invoice']
        
        # Set write-off amount to invoice balance if not specified
        write_off_amount = serializer.validated_data.get('write_off_amount')
        if not write_off_amount:
            write_off_amount = invoice.balance_amount
        
        write_off = serializer.save(
            company=company,
            write_off_amount=write_off_amount
        )
        
        # Log audit trail
        from financial.models.audit_trail import AuditTrail
        AuditTrail.log_action(
            action="write_off",
            entity_type="invoice",
            entity_id=invoice.id,
            reference=invoice.invoice_number,
            details=f"Invoice {invoice.invoice_number} written off for ₹{write_off_amount}",
            company=company,
            user=self.request.user if self.request.user.is_authenticated else None,
            changes={"status": "outstanding", "write_off_amount": str(write_off_amount)},
        )


class WriteOffSelectedView(APIView):
    """Write off multiple selected invoices"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        invoice_ids = request.data.get("invoice_ids", [])
        reason = request.data.get("reason", "Aging > 90 days")
        notes = request.data.get("notes", "")

        if not invoice_ids:
            return Response(
                {"error": "invoice_ids are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).exclude(
            write_offs__isnull=False
        )

        written_off_count = 0
        total_amount = Decimal("0.00")

        for invoice in invoices:
            balance = invoice.balance_amount
            
            # Create write-off
            write_off, created = WriteOff.objects.get_or_create(
                company=company,
                invoice=invoice,
                defaults={
                    'write_off_amount': balance,
                    'reason': reason,
                    'notes': notes,
                }
            )
            
            if created:
                written_off_count += 1
                total_amount += balance
                
                # Log audit trail
                from financial.models.audit_trail import AuditTrail
                AuditTrail.log_action(
                    action="write_off",
                    entity_type="invoice",
                    entity_id=invoice.id,
                    reference=invoice.invoice_number,
                    details=f"Invoice {invoice.invoice_number} written off for ₹{balance}",
                    company=company,
                    user=request.user if request.user.is_authenticated else None,
                    changes={"status": "outstanding", "write_off_amount": str(balance)},
                )

        return Response({
            "message": f"Successfully wrote off {written_off_count} invoices",
            "written_off_count": written_off_count,
            "total_amount": float(total_amount),
        })

