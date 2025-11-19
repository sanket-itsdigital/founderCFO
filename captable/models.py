from decimal import Decimal

from django.db import models

from backend.models import BaseModel
from captable.enums import (
    CapTableEventStatus,
    ShareClassType,
    InvestorType,
)


# Create your models here.
class CapTableEvents(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="cap_table_events",
    )
    event_name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=255, choices=CapTableEventStatus.choices)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    valuation = models.DecimalField(
        max_digits=20, decimal_places=2, blank=True, null=True
    )
    amount_raised = models.DecimalField(
        max_digits=20, decimal_places=2, blank=True, null=True
    )
    share_price = models.DecimalField(
        max_digits=20, decimal_places=4, blank=True, null=True
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "captable_events"
        verbose_name = "Cap Table Event"
        verbose_name_plural = "Cap Table Events"
        ordering = ["-date"]


class Shareholder(BaseModel):
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="shareholders"
    )
    name = models.CharField(max_length=255)
    investor_type = models.CharField(
        max_length=50, choices=InvestorType.choices, default=InvestorType.OTHER
    )
    email = models.EmailField()
    kyc_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "captable_shareholder"
        unique_together = ("company", "email")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.investor_type})"


class CapTableEventDocument(BaseModel):
    event = models.ForeignKey(
        CapTableEvents, on_delete=models.CASCADE, related_name="documents"
    )
    name = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="captable/events/%Y/%m/")

    class Meta:
        db_table = "captable_event_document"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.file.name


class CapitalizationTable(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="capitalization_rows",
    )
    event = models.ForeignKey(
        CapTableEvents, on_delete=models.CASCADE, related_name="transactions"
    )
    shareholder = models.ForeignKey(
        Shareholder, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    share_class_type = models.CharField(max_length=255, choices=ShareClassType.choices)
    share_class_name = models.CharField(max_length=255)
    shares_issued = models.DecimalField(max_digits=20, decimal_places=2)
    price_per_share = models.DecimalField(max_digits=20, decimal_places=2)
    lock_in_ends = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.share_class_name} - {self.event.event_name}"

    def save(self, *args, **kwargs):
        shares = self.shares_issued or Decimal("0")
        price = self.price_per_share or Decimal("0")
        self.amount = shares * price
        super().save(*args, **kwargs)

    class Meta:
        db_table = "captable_capitalization_table"
        verbose_name = "Capitalization Table"
        verbose_name_plural = "Capitalization Tables"
        ordering = ["-event__date"]
