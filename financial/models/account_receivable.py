from decimal import Decimal

from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import (
    InvoicesCategoryChoices,
    InvoicesPaymentTerms,
    InvoicesStatusChoices,
)


class Invoice(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=100, unique=True)
    customer_name = models.CharField(max_length=255)
    invoice_date = models.DateField()
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        choices=InvoicesPaymentTerms.choices,
    )
    due_date = models.DateField()

    # Amounts
    subtotal_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    # Payment tracking
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    balance_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    category = models.CharField(
        choices=InvoicesCategoryChoices.choices,
        max_length=50,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=InvoicesStatusChoices.choices,
        default=InvoicesStatusChoices.DRAFT,
    )
    sales_order_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "invoice"
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-invoice_date"]
        unique_together = ["company", "invoice_number"]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"

    @property
    def balance_amount(self):
        """Calculate outstanding amount: total - paid"""
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self):
        """Check if the invoice is overdue"""
        from django.utils import timezone

        return self.due_date < timezone.now().date() and self.status not in [
            InvoicesStatusChoices.PAID,
            InvoicesStatusChoices.CANCELLED,
        ]

    @property
    def amount(self):
        """Alias for total_amount for backward compatibility"""
        return self.total_amount

    def save(self, *args, **kwargs):
        """Auto-calculate total amount and update status"""
        # Calculate total if not set
        if not self.total_amount and self.subtotal_amount:
            self.total_amount = (
                self.subtotal_amount + self.tax_amount - self.discount_amount
            )

        # Auto-update status based on payments
        if self.status in [InvoicesStatusChoices.DRAFT, InvoicesStatusChoices.PENDING]:
            if self.paid_amount >= self.total_amount:
                self.status = InvoicesStatusChoices.PAID
            elif self.is_overdue:
                self.status = InvoicesStatusChoices.OVERDUE
            elif self.paid_amount > 0:
                self.status = InvoicesStatusChoices.PARTIAL
            else:
                self.status = InvoicesStatusChoices.PENDING

        super().save(*args, **kwargs)

    