from decimal import Decimal

from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import (
    DisputeReasonChoices,
    DisputeStatusChoices,
    DisputePriorityChoices,
)
from revenue.models.invoice import Invoice


class Dispute(BaseModel):
    """Invoice disputes"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="disputes",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="disputes",
    )
    reason = models.CharField(
        max_length=100,
        choices=DisputeReasonChoices.choices,
    )
    disputed_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    priority = models.CharField(
        max_length=20,
        choices=DisputePriorityChoices.choices,
        default=DisputePriorityChoices.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=DisputeStatusChoices.choices,
        default=DisputeStatusChoices.OPEN,
    )
    description = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dispute"
        verbose_name = "Dispute"
        verbose_name_plural = "Disputes"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Dispute for {self.invoice.invoice_number} - {self.get_status_display()}"
        )

    def mark_as_resolved(self, resolution_notes=""):
        """Mark dispute as resolved"""
        from django.utils import timezone

        self.status = DisputeStatusChoices.RESOLVED
        self.resolution_notes = resolution_notes
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolution_notes", "resolved_at"])
