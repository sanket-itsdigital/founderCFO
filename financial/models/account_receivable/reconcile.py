from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.models.account_receivable import Invoice


class BankTransaction(BaseModel):
    """Bank transactions for reconciliation"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="bank_transactions",
    )
    transaction_date = models.DateField()
    description = models.CharField(max_length=500)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    transaction_type = models.CharField(
        max_length=50,
        choices=[
            ("NEFT", "NEFT"),
            ("RTGS", "RTGS"),
            ("IMPS", "IMPS"),
            ("UPI", "UPI"),
            ("CHEQUE", "Cheque"),
            ("CASH", "Cash"),
            ("OTHER", "Other"),
        ],
        default="OTHER",
    )
    reference_number = models.CharField(max_length=255, blank=True)
    is_matched = models.BooleanField(default=False)
    matched_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_transactions",
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bank_transaction"
        verbose_name = "Bank Transaction"
        verbose_name_plural = "Bank Transactions"
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"{self.description} - {self.amount} - {self.transaction_date}"

    def match_with_invoice(self, invoice):
        """Match this transaction with an invoice"""
        self.is_matched = True
        self.matched_invoice = invoice
        self.matched_at = timezone.now()
        self.save(update_fields=['is_matched', 'matched_invoice', 'matched_at'])

    def unmatch(self):
        """Unmatch this transaction"""
        self.is_matched = False
        self.matched_invoice = None
        self.matched_at = None
        self.save(update_fields=['is_matched', 'matched_invoice', 'matched_at'])

