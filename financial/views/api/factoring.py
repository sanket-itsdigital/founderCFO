from decimal import Decimal
from datetime import timedelta

from django.db.models import F, Avg
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.factoring import FactoringRequest, FactoringRequestInvoice
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.factoring import (
    FactoringRequestSerializer,
    FactoringRequestCreateSerializer,
)
from financial.views.api.ar_aging import get_company_from_request


class FactoringSummaryView(APIView):
    """Get factoring summary based on selected invoices"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        invoice_ids = request.data.get("invoice_ids", [])
        advance_rate = Decimal(str(request.data.get("advance_rate", 80)))
        factoring_fee = Decimal(str(request.data.get("factoring_fee", 2.5)))

        if not invoice_ids:
            return Response({
                "selected_invoices": 0,
                "total_receivables": 0,
                "avg_days_to_due": 0,
                "advance_amount": 0,
                "factoring_fee_amount": 0,
                "net_proceeds": 0,
                "reserve_amount": 0,
                "annualized_cost": 0.0,
            })

        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        total_receivables = sum(invoice.balance_amount for invoice in invoices)
        
        # Calculate average days to due
        today = timezone.now().date()
        days_list = [(invoice.due_date - today).days for invoice in invoices]
        avg_days_to_due = int(sum(days_list) / len(days_list)) if days_list else 0

        # Calculate amounts
        advance_rate_decimal = advance_rate / 100
        advance_amount = total_receivables * advance_rate_decimal
        
        fee_rate_decimal = factoring_fee / 100
        factoring_fee_amount = total_receivables * fee_rate_decimal
        
        net_proceeds = advance_amount - factoring_fee_amount
        reserve_amount = total_receivables - advance_amount

        # Calculate annualized cost
        if advance_amount > 0 and avg_days_to_due > 0:
            cost_rate = factoring_fee_amount / advance_amount
            annualized_cost = cost_rate * (365 / avg_days_to_due) * 100
        else:
            annualized_cost = 0.0

        return Response({
            "selected_invoices": invoices.count(),
            "total_receivables": float(total_receivables),
            "total_receivables_display": f"₹{total_receivables:,.0f}",
            "avg_days_to_due": avg_days_to_due,
            "advance_amount": float(advance_amount),
            "advance_amount_display": f"₹{advance_amount:,.0f}",
            "factoring_fee_amount": float(factoring_fee_amount),
            "factoring_fee_amount_display": f"₹{factoring_fee_amount:,.0f}",
            "net_proceeds": float(net_proceeds),
            "net_proceeds_display": f"₹{net_proceeds:,.0f}",
            "reserve_amount": float(reserve_amount),
            "reserve_amount_display": f"₹{reserve_amount:,.0f}",
            "annualized_cost": round(annualized_cost, 1),
            "annualized_cost_display": f"{annualized_cost:.1f}%",
        })


class FactoringRequestListCreateView(generics.ListCreateAPIView):
    """List and create factoring requests"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FactoringRequestCreateSerializer
        return FactoringRequestSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return FactoringRequest.objects.none()
        
        queryset = FactoringRequest.objects.filter(company=company).prefetch_related('invoices__invoice')
        
        # Optional filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        invoice_ids = serializer.validated_data.pop('invoice_ids', [])
        
        # Create factoring request
        factoring_request = serializer.save(
            company=company,
            status="draft"
        )
        
        # Add invoices
        if invoice_ids:
            invoices = Invoice.objects.filter(
                id__in=invoice_ids,
                company=company
            )
            for invoice in invoices:
                FactoringRequestInvoice.objects.get_or_create(
                    factoring_request=factoring_request,
                    invoice=invoice
                )
            
            # Calculate amounts
            factoring_request.calculate_amounts(invoices)


class FactoringRequestRetrieveView(generics.RetrieveAPIView):
    """Retrieve factoring request detail"""
    permission_classes = [IsAuthenticated]
    serializer_class = FactoringRequestSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return FactoringRequest.objects.none()
        
        return FactoringRequest.objects.filter(company=company).prefetch_related('invoices__invoice')


class AvailableInvoicesListView(APIView):
    """List invoices available for factoring"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response([])

        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        today = timezone.now().date()
        invoice_list = []

        for invoice in invoices:
            days_diff = (invoice.due_date - today).days
            due_status = f"{abs(days_diff)}d overdue" if days_diff < 0 else f"{days_diff}d to due"
            
            invoice_list.append({
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer_name,
                "amount": float(invoice.balance_amount),
                "amount_display": f"₹{invoice.balance_amount:,.0f}",
                "due_date": invoice.due_date,
                "due_status": due_status,
                "is_overdue": days_diff < 0,
            })

        return Response(invoice_list)

