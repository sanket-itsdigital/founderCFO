from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.payment_plans import PaymentPlan, PaymentPlanInstallment
from financial.enums import PaymentPlanStatusChoices, InstallmentStatusChoices
from financial.serializers.payment_plans import (
    PaymentPlanSerializer,
    PaymentPlanCreateSerializer,
    PaymentPlanInstallmentSerializer,
)
from financial.views.api.ar_aging import get_company_from_request


class PaymentPlansSummaryView(APIView):
    """Get payment plans summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "active_plans": 0,
                "total_plan_value": 0,
                "collected_via_plans": 0,
                "completed_plans": 0,
            })

        active_plans = PaymentPlan.objects.filter(
            company=company,
            status=PaymentPlanStatusChoices.ACTIVE
        ).count()

        total_plan_value = PaymentPlan.objects.filter(
            company=company
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal("0.00")

        collected_via_plans = PaymentPlanInstallment.objects.filter(
            payment_plan__company=company,
            status=InstallmentStatusChoices.PAID
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal("0.00")

        completed_plans = PaymentPlan.objects.filter(
            company=company,
            status=PaymentPlanStatusChoices.COMPLETED
        ).count()

        return Response({
            "active_plans": active_plans,
            "total_plan_value": float(total_plan_value),
            "total_plan_value_display": self._in_lakhs(total_plan_value),
            "collected_via_plans": float(collected_via_plans),
            "collected_via_plans_display": f"₹{collected_via_plans:.0f}",
            "completed_plans": completed_plans,
        })

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"


class PaymentPlanListCreateView(generics.ListCreateAPIView):
    """List and create payment plans"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentPlanCreateSerializer
        return PaymentPlanSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return PaymentPlan.objects.none()
        
        queryset = PaymentPlan.objects.filter(company=company).select_related('invoice')
        
        # Optional filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        invoice = serializer.validated_data['invoice']
        
        # Set total amount from invoice balance
        total_amount = invoice.balance_amount
        
        # Create payment plan
        payment_plan = serializer.save(
            company=company,
            total_amount=total_amount,
            status=PaymentPlanStatusChoices.ACTIVE
        )
        
        # Create installments
        payment_plan.create_installments()


class PaymentPlanRetrieveView(generics.RetrieveAPIView):
    """Retrieve payment plan detail"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentPlanSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return PaymentPlan.objects.none()
        
        return PaymentPlan.objects.filter(company=company).select_related('invoice').prefetch_related('installments')


class MarkInstallmentPaidView(APIView):
    """Mark an installment as paid"""
    permission_classes = [IsAuthenticated]

    def post(self, request, installment_id, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            installment = PaymentPlanInstallment.objects.get(
                id=installment_id,
                payment_plan__company=company
            )
            payment_reference = request.data.get("payment_reference", "")
            installment.mark_as_paid(payment_reference)
            
            serializer = PaymentPlanInstallmentSerializer(installment)
            return Response(serializer.data)
        except PaymentPlanInstallment.DoesNotExist:
            return Response(
                {"error": "Installment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

