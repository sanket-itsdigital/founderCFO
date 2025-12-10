from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from revenue.models.invoice import Invoice
from financial.enums import InvoicesStatusChoices


class CashFlowProjection(BaseModel):
    """Cash flow projections for a company"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="cash_flow_projections",
    )
    projection_date = models.DateField()
    due_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    expected_collection = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    optimistic_collection = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    conservative_collection = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    projection_type = models.CharField(
        max_length=20,
        choices=[("weekly", "Weekly"), ("monthly", "Monthly")],
        default="weekly",
    )

    class Meta:
        db_table = "cash_flow_projection"
        verbose_name = "Cash Flow Projection"
        verbose_name_plural = "Cash Flow Projections"
        ordering = ["projection_date"]
        unique_together = ["company", "projection_date", "projection_type"]

    def __str__(self):
        return f"Cash Flow Projection - {self.company.name} - {self.projection_date}"
