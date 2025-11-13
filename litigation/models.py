from decimal import Decimal

from django.db import models

from backend.models import BaseModel
from backend.enums import CaseTypeChoices, CaseStatusChoices, RiskLevelChoices
from accounts.models import Company


class Case(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="cases")
    case_number = models.CharField(max_length=50)
    type = models.CharField(max_length=30, choices=CaseTypeChoices.choices)
    synopsis = models.TextField(blank=True)
    total_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    issue_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=CaseStatusChoices.choices, default=CaseStatusChoices.OPEN)
    risk = models.CharField(max_length=10, choices=RiskLevelChoices.choices, default=RiskLevelChoices.LOW)

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
