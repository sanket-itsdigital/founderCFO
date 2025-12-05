from decimal import Decimal

from accounts.models import Company
from backend.models import BaseModel
from django.db import models
from django.utils import timezone

from financial.enums import BillsStatusChoices
from financial.models.account_payable.vendor import Vendor


class Bill(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="bills",
    )
    bill_number = models.CharField(max_length=100)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="bills",
        null=True,
        blank=True,
    )
    vendor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legacy field, use vendor FK when possible",
    )
    bill_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=50,
        choices=BillsStatusChoices.choices,
        default=BillsStatusChoices.PENDING,
    )
    category = models.CharField(
        max_length=100,
        blank=True,
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "bill"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-bill_date"]
        unique_together = ["company", "bill_number"]

    def __str__(self):
        return f"{self.bill_number} - {self.get_vendor_name()}"

    def get_vendor_name(self):
        """Get vendor name from FK or legacy field"""
        if self.vendor:
            return self.vendor.name
        return self.vendor_name or "Unknown Vendor"

    @property
    def balance_amount(self):
        """Calculate outstanding amount: amount - paid_amount"""
        return self.amount - self.paid_amount

    @property
    def is_overdue(self):
        """Check if the bill is overdue"""
        return (
            self.due_date < timezone.now().date()
            and self.status not in [BillsStatusChoices.PAID, BillsStatusChoices.CANCELLED]
        )

    def save(self, *args, **kwargs):
        """Auto-calculate balance and update status"""
        # Auto-update status based on payments
        if self.status in [BillsStatusChoices.PENDING, BillsStatusChoices.PARTIAL]:
            if self.paid_amount >= self.amount:
                self.status = BillsStatusChoices.PAID
            elif self.is_overdue:
                self.status = BillsStatusChoices.OVERDUE
            elif self.paid_amount > 0:
                self.status = BillsStatusChoices.PARTIAL
            else:
                self.status = BillsStatusChoices.PENDING

        # Sync vendor_name if vendor FK is set
        if self.vendor and not self.vendor_name:
            self.vendor_name = self.vendor.name

        super().save(*args, **kwargs)
