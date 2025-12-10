from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from sales.enums import (
    SalesNextStepChoices,
    SalesProductChoices,
    SalesSourceChoices,
    SalesStageStatusChoices,
)
from sales.models.sales_team import SalesTeam


class Sales(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    deal_id = models.CharField(max_length=100)
    deal_name = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    mrr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monthly Recurring Revenue",
    )
    stage = models.CharField(
        choices=SalesStageStatusChoices.choices,
        default=SalesStageStatusChoices.DISCOVERY,
        max_length=50,
    )
    client = models.CharField(max_length=255)
    sales_team = models.ForeignKey(
        SalesTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        help_text="Sales team member assigned to this deal",
    )
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Probability percentage of closing the deal (0-100)",
    )
    close_date = models.DateField(null=True, blank=True)
    subscription_product = models.CharField(
        max_length=50,
        choices=SalesProductChoices.choices,
        blank=True,
        null=True,
    )
    contract_term_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of the contract in months",
    )
    days_in_stage = models.PositiveIntegerField(
        default=0,
        help_text="Number of days the deal has been in the current stage",
    )
    last_activity = models.DateField(null=True, blank=True)
    source = models.CharField(
        choices=SalesSourceChoices.choices,
        max_length=50,
        null=True,
        blank=True,
        help_text="Source of the lead/deal",
    )
    next_step = models.CharField(
        choices=SalesNextStepChoices.choices,
        max_length=50,
        null=True,
        blank=True,
        help_text="Next action step in the sales process",
    )
    lost_reason = models.TextField(null=True, blank=True)
    competitors = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def clean(self):
        """Validate model fields"""
        super().clean()
        # Validate probability is between 0 and 100
        if self.probability < Decimal("0.00") or self.probability > Decimal("100.00"):
            raise ValidationError(
                {"probability": "Probability must be between 0.00 and 100.00"}
            )

    class Meta:
        db_table = "sales"
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ["-created_at"]
        unique_together = ["company", "deal_id"]

    def __str__(self):
        return f"{self.deal_name} - {self.deal_id}"
