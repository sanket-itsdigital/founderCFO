from decimal import Decimal
from datetime import timedelta
from calendar import monthrange

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel


class BudgetPeriodTypeChoices(models.TextChoices):
    """Period type choices for budget entries"""

    MONTHLY = "Monthly", "Monthly"
    QUARTERLY = "Quarterly", "Quarterly"
    SEMI_ANNUAL = "Semi-annual", "Semi-annual"
    ANNUAL = "Annual", "Annual"


class ExpenseBudget(BaseModel):
    """Model for managing expense budgets by category and department"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="expense_budgets",
    )

    # Budget Information
    category = models.CharField(
        max_length=255,
        help_text="Expense category (e.g., Technology & Infrastructure, Personnel Expenses)",
    )
    department = models.CharField(
        max_length=255,
        blank=True,
        help_text="Department name (optional)",
    )
    period_type = models.CharField(
        max_length=20,
        choices=BudgetPeriodTypeChoices.choices,
        default=BudgetPeriodTypeChoices.MONTHLY,
        help_text="Period type for this budget (Monthly, Quarterly, etc.)",
    )
    period = models.DateField(
        help_text="Start date of the budget period (e.g., 2025-12-01 for December 2025)",
    )
    budget_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Budgeted amount for this period",
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this budget",
    )

    class Meta:
        db_table = "expense_budget"
        verbose_name = "Expense Budget"
        verbose_name_plural = "Expense Budgets"
        ordering = ["-period", "category", "department"]
        unique_together = [
            ["company", "category", "department", "period_type", "period"],
        ]

    def __str__(self):
        dept = f" - {self.department}" if self.department else ""
        return f"{self.category} - {self.period.strftime('%Y-%m')}{dept}"

    def get_period_start(self):
        """Get the start date of the budget period"""
        return self.period.replace(day=1)

    def get_period_end(self):
        """Get the end date of the budget period based on period_type"""
        period_start = self.get_period_start()

        if self.period_type == BudgetPeriodTypeChoices.MONTHLY:
            last_day = monthrange(period_start.year, period_start.month)[1]
            return period_start.replace(day=last_day)
        elif self.period_type == BudgetPeriodTypeChoices.QUARTERLY:
            # Calculate quarter end
            quarter = (period_start.month - 1) // 3 + 1
            quarter_end_month = quarter * 3
            last_day = monthrange(period_start.year, quarter_end_month)[1]
            return period_start.replace(month=quarter_end_month, day=last_day)
        elif self.period_type == BudgetPeriodTypeChoices.SEMI_ANNUAL:
            # First half: Jan-Jun, Second half: Jul-Dec
            if period_start.month <= 6:
                return period_start.replace(month=6, day=30)
            else:
                return period_start.replace(month=12, day=31)
        elif self.period_type == BudgetPeriodTypeChoices.ANNUAL:
            return period_start.replace(month=12, day=31)
        else:
            # Default to month end
            last_day = monthrange(period_start.year, period_start.month)[1]
            return period_start.replace(day=last_day)

    def calculate_actual_amount(self, period_start=None, period_end=None):
        """Calculate actual spending from Bills for this budget's period and category/department"""
        from expense.models.bills import Bill
        from financial.enums import BillsStatusChoices

        if period_start is None:
            period_start = self.get_period_start()
        if period_end is None:
            period_end = self.get_period_end()

        # Filter bills by company, date range, category, and status
        bills = Bill.objects.filter(
            company=self.company,
            bill_date__gte=period_start,
            bill_date__lte=period_end,
            category=self.category,
        ).exclude(status=BillsStatusChoices.CANCELLED)

        # If department is specified, filter by department
        if self.department:
            bills = bills.filter(department=self.department)

        # Sum total amounts
        actual = sum(bill.total for bill in bills)
        return actual

    def get_variance(self, period_start=None, period_end=None):
        """Calculate variance: budget - actual"""
        actual = self.calculate_actual_amount(period_start, period_end)
        return self.budget_amount - actual

    def get_utilization_percentage(self, period_start=None, period_end=None):
        """Calculate utilization percentage: (actual / budget) * 100"""
        if self.budget_amount == 0:
            return 0.0
        actual = self.calculate_actual_amount(period_start, period_end)
        return float((actual / self.budget_amount) * 100)

    def get_status(self, period_start=None, period_end=None):
        """Get budget status based on utilization"""
        utilization = self.get_utilization_percentage(period_start, period_end)

        if utilization >= 100:
            return "Over Budget"
        elif utilization >= 90:
            return "Warning"
        elif utilization >= 75:
            return "On Track"
        else:
            return "Under Budget"
