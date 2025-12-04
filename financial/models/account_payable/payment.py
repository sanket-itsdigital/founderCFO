from decimal import Decimal

from accounts.models import Company
from backend.models import BaseModel
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from financial.models.account_payable.bills import Bill


class PaymentMethodChoices(models.TextChoices):
    BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
    NEFT = "NEFT", "NEFT"
    RTGS = "RTGS", "RTGS"
    IMPS = "IMPS", "IMPS"
    CHEQUE = "Cheque", "Cheque"
    UPI = "UPI", "UPI"
    CASH = "Cash", "Cash"
    CREDIT_CARD = "Credit Card", "Credit Card"


class BillPayment(BaseModel):
    """Payment records for bills"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="bill_payments",
    )
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethodChoices.choices,
        default=PaymentMethodChoices.BANK_TRANSFER,
    )
    reference_number = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    tds_deducted = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="TDS deducted from payment",
    )
    discount_taken = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Discount taken on payment",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "bill_payment"
        verbose_name = "Bill Payment"
        verbose_name_plural = "Bill Payments"
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"Payment for {self.bill.bill_number} - {self.amount} on {self.payment_date}"

    def save(self, *args, **kwargs):
        """Update bill paid_amount when payment is saved"""
        super().save(*args, **kwargs)
        
        # Recalculate bill's paid_amount from all payments
        total_paid = self.bill.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal("0.00")
        
        # Update bill's paid_amount
        self.bill.paid_amount = total_paid
        self.bill.updated_by = self.updated_by
        self.bill.save(update_fields=['paid_amount', 'updated_by', 'updated_at'])

    def delete(self, *args, **kwargs):
        """Update bill paid_amount when payment is deleted"""
        bill = self.bill
        super().delete(*args, **kwargs)
        
        # Recalculate bill's paid_amount from remaining payments
        total_paid = bill.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal("0.00")
        
        bill.paid_amount = total_paid
        bill.save(update_fields=['paid_amount', 'updated_at'])

