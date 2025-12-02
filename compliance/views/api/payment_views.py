from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from compliance.models import CompliancePayments, ComplianceTaskMaster
from compliance.serializers import CompliancePaymentSerializer
from compliance.views.api.task_views import get_company_from_request


class CompliancePaymentListCreateView(generics.ListCreateAPIView):
    """
    List all compliance payments or create a new one.
    """

    queryset = CompliancePayments.objects.all()
    serializer_class = CompliancePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CompliancePayments.objects.all()

        # For non-superusers, filter by company's selected tasks
        if not self.request.user.is_superuser:
            company = get_company_from_request(self.request)
            if company:
                # Get task IDs for company's selected tasks
                company_task_ids = company.selected_compliance_tasks.values_list(
                    "id", flat=True
                )
                queryset = queryset.filter(compliance_task_id__in=company_task_ids)
            else:
                queryset = queryset.none()

        # Filter by task_id if provided
        task_id = self.request.query_params.get("task_id", None)
        if task_id:
            queryset = queryset.filter(task_id=task_id)

        # Filter by related_act if provided
        related_act = self.request.query_params.get("related_act", None)
        if related_act:
            queryset = queryset.filter(related_act=related_act)

        # Filter by is_late if provided
        is_late = self.request.query_params.get("is_late", None)
        if is_late is not None:
            queryset = queryset.filter(is_late=is_late.lower() == "true")

        return queryset.order_by("-payment_date", "-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class CompliancePaymentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a compliance payment.
    For regular users: Only allows access to payments for tasks selected by their company.
    For superusers: Allows access to all payments.
    """

    queryset = CompliancePayments.objects.all()
    serializer_class = CompliancePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CompliancePayments.objects.all()

        # For non-superusers, filter by company's selected tasks
        if not self.request.user.is_superuser:
            company = get_company_from_request(self.request)
            if company:
                # Get task IDs for company's selected tasks
                company_task_ids = company.selected_compliance_tasks.values_list(
                    "id", flat=True
                )
                queryset = queryset.filter(compliance_task_id__in=company_task_ids)
            else:
                queryset = queryset.none()

        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CompliancePaymentDashboardView(APIView):
    """
    Payment-focused dashboard derived from ComplianceTaskMaster.payment_amount.

    Returns total outflow (all time), current month outflow with month-over-month
    change, and the single largest payment (amount + metadata).
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        queryset = ComplianceTaskMaster.objects.exclude(payment_amount__isnull=True)

        # Include zero-value rows so users can see counts, but calculations drop them later.
        if not request.user.is_superuser:
            company = get_company_from_request(request)
            if company:
                queryset = queryset.filter(companies=company)
            else:
                return ComplianceTaskMaster.objects.none()
        return queryset

    @staticmethod
    def _sum_amount(queryset):
        return queryset.aggregate(
            total=Coalesce(
                Sum("payment_amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        )["total"] or Decimal("0")

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request, *args, **kwargs):
        tasks = self.get_queryset(request)
        total_outflow = self._sum_amount(tasks)

        today = timezone.now().date()
        start_this_month = today.replace(day=1)
        last_month_end = start_this_month - timedelta(days=1)
        start_last_month = last_month_end.replace(day=1)

        this_month_total = self._sum_amount(
            tasks.filter(
                payment_period__gte=start_this_month, payment_period__lte=today
            )
        )
        last_month_total = self._sum_amount(
            tasks.filter(
                payment_period__gte=start_last_month, payment_period__lte=last_month_end
            )
        )

        if last_month_total and last_month_total > 0:
            trend_percent = float(
                ((this_month_total - last_month_total) / last_month_total) * 100
            )
        else:
            trend_percent = 0.0

        largest_payment = (
            tasks.exclude(payment_amount__lte=0)
            .order_by("-payment_amount", "-payment_period")
            .first()
        )
        largest_payment_data = (
            {
                "task_id": largest_payment.task_id,
                "act": largest_payment.act,
                "particulars": largest_payment.particulars,
                "payment_period": largest_payment.payment_period,
                "payment_amount": float(largest_payment.payment_amount),
                "payment_amount_display": self._in_lakhs(
                    largest_payment.payment_amount or Decimal("0")
                ),
                "payment_method": largest_payment.payment_method,
            }
            if largest_payment
            else None
        )

        response_payload = {
            "total_tax_outflow": {
                "amount": float(total_outflow),
                "display": self._in_lakhs(total_outflow),
                "records": tasks.count(),
            },
            "this_month": {
                "amount": float(this_month_total),
                "display": self._in_lakhs(this_month_total),
                "trend_percent": trend_percent,
            },
            "largest_payment": largest_payment_data,
        }

        return Response(response_payload)
