from decimal import Decimal
from datetime import timedelta, date
from calendar import monthrange
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.models.account_payable.vendor import Vendor


class RecurringExpenseFrequencyChoices(models.TextChoices):
    """Frequency choices for recurring expenses"""

    MONTHLY = "Monthly", "Monthly"
    QUARTERLY = "Quarterly", "Quarterly"
    SEMI_ANNUAL = "Semi-annual", "Semi-annual"
    ANNUAL = "Annual", "Annual"


class RecurringExpenseStatusChoices(models.TextChoices):
    """Status choices for recurring expenses"""

    ACTIVE = "Active", "Active"
    EXPIRED = "Expired", "Expired"
    CANCELLED = "Cancelled", "Cancelled"
    PAUSED = "Paused", "Paused"


class RecurringExpense(BaseModel):
    """Model for managing recurring expenses and subscriptions"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="recurring_expenses",
    )

    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text="Name of the recurring expense (e.g., 'Software Subscription')",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
        null=True,
        blank=True,
    )
    vendor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Vendor/Service name (e.g., AWS, HubSpot, WeWork)",
    )
    description = models.TextField(
        blank=True,
        help_text="Brief description of the recurring expense",
    )

    # Category Information
    category = models.CharField(
        max_length=255,
        help_text="Expense category (e.g., Technology & Infrastructure, Personnel Expenses)",
    )
    sub_category = models.CharField(
        max_length=255,
        blank=True,
        help_text="Sub-category (e.g., Productivity Tools)",
    )

    # Financial Information
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Base amount of the recurring expense",
    )
    tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Tax amount",
    )

    # Frequency and Dates
    frequency = models.CharField(
        max_length=20,
        choices=RecurringExpenseFrequencyChoices.choices,
        default=RecurringExpenseFrequencyChoices.MONTHLY,
        help_text="How often the expense recurs",
    )
    start_date = models.DateField(
        help_text="Start date of the recurring expense",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date of the contract (optional)",
    )

    # Contract Information
    contract_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Contract ID or reference",
    )

    # Auto-generation Settings
    auto_generate_expenses = models.BooleanField(
        default=True,
        help_text="Automatically create expense entries when due",
    )
    days_before_due_to_generate = models.PositiveIntegerField(
        default=7,
        help_text="Number of days before due date to generate the expense",
    )
    renewal_reminder_days = models.PositiveIntegerField(
        default=30,
        help_text="Number of days before renewal to send reminder",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=RecurringExpenseStatusChoices.choices,
        default=RecurringExpenseStatusChoices.ACTIVE,
    )

    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text="Additional notes",
    )

    class Meta:
        db_table = "expense_recurring_expense"
        verbose_name = "Recurring Expense"
        verbose_name_plural = "Recurring Expenses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.get_vendor_display()} ({self.get_frequency_display()})"

    def get_vendor_display(self):
        """Get vendor name for display"""
        if self.vendor:
            return self.vendor.name
        return self.vendor_name or "Unknown Vendor"

    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency and start date"""
        today = timezone.now().date()
        current_date = self.start_date

        # Calculate next due date
        while current_date <= today:
            if self.frequency == RecurringExpenseFrequencyChoices.MONTHLY:
                # Add 1 month
                if current_date.month == 12:
                    new_year = current_date.year + 1
                    new_month = 1
                else:
                    new_year = current_date.year
                    new_month = current_date.month + 1

                # Handle day overflow (e.g., Jan 31 -> Feb 28/29)
                try:
                    current_date = date(new_year, new_month, current_date.day)
                except ValueError:
                    last_day = monthrange(new_year, new_month)[1]
                    current_date = date(
                        new_year, new_month, min(current_date.day, last_day)
                    )

            elif self.frequency == RecurringExpenseFrequencyChoices.QUARTERLY:
                # Add 3 months
                months_to_add = 3
                new_month = current_date.month + months_to_add
                new_year = current_date.year
                if new_month > 12:
                    new_year += 1
                    new_month -= 12

                try:
                    current_date = date(new_year, new_month, current_date.day)
                except ValueError:
                    last_day = monthrange(new_year, new_month)[1]
                    current_date = date(
                        new_year, new_month, min(current_date.day, last_day)
                    )

            elif self.frequency == RecurringExpenseFrequencyChoices.SEMI_ANNUAL:
                # Add 6 months
                months_to_add = 6
                new_month = current_date.month + months_to_add
                new_year = current_date.year
                if new_month > 12:
                    new_year += 1
                    new_month -= 12

                try:
                    current_date = date(new_year, new_month, current_date.day)
                except ValueError:
                    last_day = monthrange(new_year, new_month)[1]
                    current_date = date(
                        new_year, new_month, min(current_date.day, last_day)
                    )

            elif self.frequency == RecurringExpenseFrequencyChoices.ANNUAL:
                # Add 1 year
                try:
                    current_date = date(
                        current_date.year + 1, current_date.month, current_date.day
                    )
                except ValueError:
                    # Handle leap year edge case (Feb 29)
                    last_day = monthrange(current_date.year + 1, current_date.month)[1]
                    current_date = date(
                        current_date.year + 1,
                        current_date.month,
                        min(current_date.day, last_day),
                    )

            # Check if end_date is set and we've passed it
            if self.end_date and current_date > self.end_date:
                return None

        return current_date

    def is_due_soon(self, days=7):
        """Check if the expense is due within the specified number of days"""
        next_due = self.calculate_next_due_date()
        if not next_due:
            return False
        today = timezone.now().date()
        days_until_due = (next_due - today).days
        return 0 <= days_until_due <= days

    def is_overdue(self):
        """Check if the expense is overdue"""
        next_due = self.calculate_next_due_date()
        if not next_due:
            return False
        today = timezone.now().date()
        return next_due < today

    def get_total_amount(self):
        """Get total amount including tax"""
        return self.amount + self.tax

    def save(self, *args, **kwargs):
        """Override save to update status based on dates"""
        today = timezone.now().date()

        # Update status based on end_date
        if self.end_date and self.end_date < today:
            if self.status == RecurringExpenseStatusChoices.ACTIVE:
                self.status = RecurringExpenseStatusChoices.EXPIRED
        elif self.status == RecurringExpenseStatusChoices.EXPIRED and (
            not self.end_date or self.end_date >= today
        ):
            self.status = RecurringExpenseStatusChoices.ACTIVE

        super().save(*args, **kwargs)
