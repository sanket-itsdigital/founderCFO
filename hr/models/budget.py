from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from backend.models import BaseModel


class Budget(BaseModel):
    """HR Budget model for tracking budget vs actual spending"""

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="hr_budgets",
    )
    period = models.DateField(
        help_text="Period for this budget entry (typically first day of month for monthly budgets)"
    )
    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        related_name="budgets",
        null=True,
        blank=True,
    )
    budget_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    actual_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hr_budget"
        verbose_name = "HR Budget"
        verbose_name_plural = "HR Budgets"
        ordering = ["-period", "category"]
        unique_together = [
            ["company", "period", "category", "department"],
        ]

    def __str__(self):
        dept = f" - {self.department.name}" if self.department else ""
        return f"{self.category.name} - {self.period.strftime('%Y-%m')}{dept}"

    @property
    def variance(self):
        """Calculate variance: actual - budget"""
        return self.actual_amount - self.budget_amount

    @property
    def variance_percentage(self):
        """Calculate variance percentage: (variance / budget) * 100"""
        if self.budget_amount > 0:
            return (self.variance / self.budget_amount) * Decimal("100")
        return Decimal("0.00")

    @property
    def status(self):
        """Determine status based on variance"""
        variance_pct = self.variance_percentage
        if variance_pct < -1:
            return "Under"
        elif variance_pct > 1:
            return "Over"
        else:
            return "On Track"
