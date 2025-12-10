from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from revenue.models.invoice import Invoice


class WriteOff(BaseModel):
    """Invoice write-offs"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="write_offs",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="write_offs",
    )
    write_off_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    reason = models.CharField(
        max_length=255, default="Aging > 90 days", help_text="Reason for write-off"
    )
    write_off_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "write_off"
        verbose_name = "Write Off"
        verbose_name_plural = "Write Offs"
        ordering = ["-write_off_date"]
        unique_together = ["company", "invoice"]

    def __str__(self):
        return f"Write-off for {self.invoice.invoice_number} - {self.write_off_amount}"
