from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models.expenses.bills import Bill
from financial.models.account_payable.payment import BillPayment
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.record_payment import (
    RecordPaymentSerializer,
    RecordPaymentResponseSerializer,
)
from financial.views.api.account_payable.ap_aging import get_company_from_request


class RecordPaymentView(APIView):
    """
    API view to record a payment for a bill.

    POST: Records payment and updates bill status
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _in_thousands(amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return RecordPaymentView._in_lakhs(amount)
        else:
            return RecordPaymentView._in_thousands(amount)

    def post(self, request, *args, **kwargs):
        """Record payment for a bill"""
        company = get_company_from_request(request)
        if not company:
            raise ValidationError(
                {
                    "company": "Company is required. Please provide company_id in query params or ensure you own a company."
                }
            )

        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bill_id = serializer.validated_data["bill_id"]
        payment_amount = Decimal(str(serializer.validated_data["amount"]))
        tds_deducted = Decimal(str(serializer.validated_data.get("tds_deducted", 0)))
        discount_taken = Decimal(
            str(serializer.validated_data.get("discount_taken", 0))
        )

        # Get bill
        try:
            bill = Bill.objects.get(id=bill_id, company=company)
        except Bill.DoesNotExist:
            raise ValidationError({"bill_id": "Bill not found"})

        # Validate payment amount
        balance = bill.balance_amount
        total_payment = payment_amount + tds_deducted + discount_taken

        if total_payment > balance:
            raise ValidationError(
                {
                    "amount": f"Payment amount (including TDS and discount) cannot exceed balance due of {self._format_amount_display(balance)}"
                }
            )

        # Create payment record
        payment = BillPayment.objects.create(
            company=company,
            bill=bill,
            payment_date=serializer.validated_data["payment_date"],
            amount=payment_amount,
            payment_method=serializer.validated_data["payment_method"],
            reference_number=serializer.validated_data.get("reference_number", ""),
            bank_name=serializer.validated_data.get("bank_name", ""),
            tds_deducted=tds_deducted,
            discount_taken=discount_taken,
            notes=serializer.validated_data.get("notes", ""),
            created_by=request.user,
            updated_by=request.user,
        )

        # Bill's paid_amount is automatically updated by BillPayment.save()
        # Refresh bill to get updated status
        bill.refresh_from_db()

        # Log audit trail if available
        try:
            from financial.models.account_receivable.audit_trail import AuditTrail

            AuditTrail.log_action(
                action="payment",
                entity_type="bill",
                entity_id=str(bill.id),
                reference=bill.bill_number,
                details=f"Payment of {self._format_amount_display(payment_amount)} recorded for {bill.bill_number}",
                company=company,
                user=request.user if request.user.is_authenticated else None,
                changes={
                    "payment_amount": str(payment_amount),
                    "payment_method": serializer.validated_data["payment_method"],
                    "bill_status": bill.status,
                },
            )
        except Exception:
            # Audit trail is optional
            pass

        response_data = {
            "payment_id": str(payment.id),
            "bill_id": str(bill.id),
            "bill_number": bill.bill_number,
            "payment_date": payment.payment_date,
            "amount": float(payment_amount),
            "amount_display": self._format_amount_display(payment_amount),
            "payment_method": payment.payment_method,
            "bill_status": bill.status,
            "bill_balance": float(bill.balance_amount),
            "bill_balance_display": self._format_amount_display(bill.balance_amount),
            "message": f"Payment of {self._format_amount_display(payment_amount)} recorded successfully. Bill status: {bill.get_status_display()}",
        }

        response_serializer = RecordPaymentResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.validated_data, status=status.HTTP_201_CREATED
        )
