from decimal import Decimal
from django.db.models import Sum, Count, F
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.reconcile import BankTransaction
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.reconcile import BankTransactionSerializer, UnmatchedInvoiceSerializer
from financial.views.api.ar_aging import get_company_from_request


class ReconcileSummaryView(APIView):
    """Get reconciliation summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "unmatched_transactions_count": 0,
                "unmatched_transactions_amount": 0,
                "matched_transactions_count": 0,
                "matched_transactions_amount": 0,
                "unmatched_invoices_count": 0,
                "unmatched_invoices_amount": 0,
                "match_rate": 0.0,
            })

        unmatched_transactions = BankTransaction.objects.filter(
            company=company,
            is_matched=False
        )
        unmatched_count = unmatched_transactions.count()
        unmatched_amount = unmatched_transactions.aggregate(
            total=Sum('amount')
        )['total'] or Decimal("0.00")

        matched_transactions = BankTransaction.objects.filter(
            company=company,
            is_matched=True
        )
        matched_count = matched_transactions.count()
        matched_amount = matched_transactions.aggregate(
            total=Sum('amount')
        )['total'] or Decimal("0.00")

        unmatched_invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        ).exclude(
            matched_transactions__isnull=False
        )
        unmatched_invoices_count = unmatched_invoices.count()
        unmatched_invoices_amount = unmatched_invoices.aggregate(
            total=Sum(F('total_amount') - F('paid_amount'))
        )['total'] or Decimal("0.00")

        total_transactions = unmatched_count + matched_count
        match_rate = (matched_count / total_transactions * 100) if total_transactions > 0 else 0.0

        return Response({
            "unmatched_transactions_count": unmatched_count,
            "unmatched_transactions_amount": float(unmatched_amount),
            "unmatched_transactions_amount_display": f"₹{unmatched_amount:,.0f}",
            "matched_transactions_count": matched_count,
            "matched_transactions_amount": float(matched_amount),
            "matched_transactions_amount_display": f"₹{matched_amount:,.0f}",
            "unmatched_invoices_count": unmatched_invoices_count,
            "unmatched_invoices_amount": float(unmatched_invoices_amount),
            "unmatched_invoices_amount_display": f"₹{unmatched_invoices_amount:,.0f}",
            "match_rate": round(match_rate, 1),
        })


class BankTransactionListCreateView(generics.ListCreateAPIView):
    """List and create bank transactions"""
    permission_classes = [IsAuthenticated]
    serializer_class = BankTransactionSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return BankTransaction.objects.none()
        
        queryset = BankTransaction.objects.filter(company=company)
        
        # Filter by matched status
        is_matched = self.request.query_params.get("is_matched")
        if is_matched is not None:
            queryset = queryset.filter(is_matched=is_matched.lower() == "true")
        
        return queryset.order_by("-transaction_date")

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        serializer.save(company=company)


class UnmatchedInvoicesListView(generics.ListAPIView):
    """List unmatched invoices"""
    permission_classes = [IsAuthenticated]
    serializer_class = UnmatchedInvoiceSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return Invoice.objects.none()
        
        return Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        ).exclude(
            matched_transactions__isnull=False
        ).order_by("invoice_number")


class MatchTransactionView(APIView):
    """Match a bank transaction with an invoice"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        transaction_id = request.data.get("transaction_id")
        invoice_id = request.data.get("invoice_id")

        if not transaction_id or not invoice_id:
            return Response(
                {"error": "transaction_id and invoice_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction = BankTransaction.objects.get(id=transaction_id, company=company)
            invoice = Invoice.objects.get(id=invoice_id, company=company)
            
            transaction.match_with_invoice(invoice)
            
            serializer = BankTransactionSerializer(transaction)
            return Response(serializer.data)
        except (BankTransaction.DoesNotExist, Invoice.DoesNotExist):
            return Response(
                {"error": "Transaction or Invoice not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class AutoMatchView(APIView):
    """Auto-match bank transactions with invoices"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get unmatched transactions
        unmatched_transactions = BankTransaction.objects.filter(
            company=company,
            is_matched=False
        )

        # Get unmatched invoices
        unmatched_invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        ).exclude(
            matched_transactions__isnull=False
        )

        matched_count = 0
        
        for transaction in unmatched_transactions:
            # Try to find matching invoice by amount
            matching_invoice = unmatched_invoices.filter(
                balance_amount=transaction.amount
            ).first()
            
            if matching_invoice:
                transaction.match_with_invoice(matching_invoice)
                matched_count += 1

        return Response({
            "message": f"Matched {matched_count} transactions",
            "matched_count": matched_count,
        })

