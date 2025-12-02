from decimal import Decimal

from django.db import models

from backend.models import BaseModel
from backend.enums import (
    CaseTypeChoices,
    CaseStatusChoices,
    RiskLevelChoices,
    SuccessLikelihoodChoices,
)
from accounts.models import Company


class Case(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="cases")
    case_number = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True, default="")
    act_section = models.CharField(max_length=150, blank=True, default="")
    authority = models.CharField(max_length=150, blank=True, default="")
    type = models.CharField(max_length=30, choices=CaseTypeChoices.choices)
    synopsis = models.TextField(blank=True)
    demand_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    interest_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    penalty_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    provision_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    total_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    issue_date = models.DateField()
    service_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    hearing_date = models.DateField(blank=True, null=True)
    final_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=CaseStatusChoices.choices, default=CaseStatusChoices.OPEN)
    risk = models.CharField(max_length=10, choices=RiskLevelChoices.choices, default=RiskLevelChoices.LOW)
    likelihood_of_success = models.CharField(
        max_length=10,
        choices=SuccessLikelihoodChoices.choices,
        default=SuccessLikelihoodChoices.MEDIUM,
    )
    internal_responsible_person = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    responsible_email = models.EmailField(blank=True)
    consultant_name = models.CharField(max_length=120, blank=True)
    consultant_firm = models.CharField(max_length=150, blank=True)
    consultant_contact = models.CharField(max_length=25, blank=True)
    notes = models.TextField(blank=True)
    resolution_details = models.TextField(blank=True)

    class Meta:
        db_table = "litigation_case"
        verbose_name = "Case"
        verbose_name_plural = "Cases"
        indexes = [
            models.Index(fields=["company", "type"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "risk"]),
        ]

    def __str__(self):
        return f"{self.case_number} - {self.type}"

    def calculate_total_exposure(self) -> Decimal:
        return (
            (self.demand_amount or Decimal("0.00"))
            + (self.interest_amount or Decimal("0.00"))
            + (self.penalty_amount or Decimal("0.00"))
            + (self.provision_amount or Decimal("0.00"))
        )

    def save(self, *args, **kwargs):
        self.total_exposure = self.calculate_total_exposure()
        super().save(*args, **kwargs)
