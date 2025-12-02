from decimal import Decimal
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.discounts import DiscountProgram
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.discounts import DiscountProgramSerializer, EligibleInvoiceSerializer
from financial.views.api.ar_aging import get_company_from_request


class DiscountsSummaryView(APIView):
    """Get discounts summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "eligible_invoices_count": 0,
                "eligible_amount": 0,
                "potential_savings": 0,
                "avg_discount_rate": 0.0,
            })

        # Get active discount programs
        active_programs = DiscountProgram.objects.filter(
            Q(company=company) | Q(company__isnull=True),
            is_active=True
        )

        if not active_programs.exists():
            return Response({
                "eligible_invoices_count": 0,
                "eligible_amount": 0,
                "eligible_amount_display": "₹0",
                "potential_savings": 0,
                "potential_savings_display": "₹0",
                "avg_discount_rate": 0.0,
            })

        # Get eligible invoices (not paid, not cancelled, within discount period)
        today = timezone.now().date()
        eligible_invoices = []
        total_eligible_amount = Decimal("0")
        total_savings = Decimal("0")
        discount_rates = []

        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        for invoice in invoices:
            for program in active_programs:
                discount_deadline = invoice.due_date - timedelta(days=program.discount_days)
                if today <= discount_deadline:
                    eligible_invoices.append(invoice)
                    balance = invoice.balance_amount
                    total_eligible_amount += balance
                    savings = balance * (program.discount_percentage / 100)
                    total_savings += savings
                    discount_rates.append(float(program.discount_percentage))
                    break  # Use best discount (first match)

        avg_discount_rate = sum(discount_rates) / len(discount_rates) if discount_rates else 0.0

        return Response({
            "eligible_invoices_count": len(set(eligible_invoices)),
            "eligible_amount": float(total_eligible_amount),
            "eligible_amount_display": f"₹{total_eligible_amount:,.0f}",
            "potential_savings": float(total_savings),
            "potential_savings_display": f"₹{total_savings:,.0f}",
            "avg_discount_rate": round(avg_discount_rate, 1),
        })


class DiscountProgramListCreateView(generics.ListCreateAPIView):
    """List and create discount programs"""
    permission_classes = [IsAuthenticated]
    serializer_class = DiscountProgramSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        # Get company-specific and global programs
        queryset = DiscountProgram.objects.filter(
            Q(company=company) | Q(company__isnull=True)
        )
        return queryset.order_by('program_name')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        serializer.save(company=company)


class DiscountProgramRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete discount program"""
    permission_classes = [IsAuthenticated]
    serializer_class = DiscountProgramSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        return DiscountProgram.objects.filter(
            Q(company=company) | Q(company__isnull=True)
        )


class EligibleInvoicesListView(APIView):
    """List invoices eligible for early payment discount"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response([])

        # Get active discount programs
        active_programs = DiscountProgram.objects.filter(
            Q(company=company) | Q(company__isnull=True),
            is_active=True
        ).order_by('-discount_percentage')  # Best discount first

        if not active_programs.exists():
            return Response([])

        today = timezone.now().date()
        eligible_invoices_data = []

        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        for invoice in invoices:
            best_discount = None
            best_savings = Decimal("0")
            best_deadline = None

            for program in active_programs:
                discount_deadline = invoice.due_date - timedelta(days=program.discount_days)
                if today <= discount_deadline:
                    balance = invoice.balance_amount
                    savings = balance * (program.discount_percentage / 100)
                    if savings > best_savings:
                        best_discount = program
                        best_savings = savings
                        best_deadline = discount_deadline

            if best_discount:
                eligible_invoices_data.append({
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "customer_name": invoice.customer_name,
                    "amount": float(invoice.balance_amount),
                    "amount_display": f"₹{invoice.balance_amount:,.0f}",
                    "best_discount": f"{best_discount.discount_percentage}% / {best_discount.discount_days}d",
                    "savings": float(best_savings),
                    "savings_display": f"₹{best_savings:,.0f}",
                    "deadline": best_deadline,
                    "deadline_display": best_deadline.strftime("%d %b"),
                })

        serializer = EligibleInvoiceSerializer(data=eligible_invoices_data, many=True)
        serializer.is_valid()
        return Response(serializer.data)

