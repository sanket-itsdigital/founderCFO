from datetime import datetime, timedelta, date
from calendar import monthrange
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from backend.enums import ActNameChoices, ComplianceStatusChoices
from backend.models import BaseModel
from compliance.enums import (
    CompanyType,
    ConsequencesType,
    Frequency,
    InterestType,
    ParticularsType,
    PenaltyAmount,
)
from accounts.models import Company


# Create your models here.
class ComplianceTaskMaster(BaseModel):
    act = models.CharField(
        max_length=255,
        choices=ActNameChoices.choices,
    )
    particulars = models.TextField(choices=ParticularsType.choices)
    due_date = models.DateField()

    frequency = models.CharField(max_length=100, choices=Frequency.choices)
    severity = models.CharField(max_length=50)
    status = models.CharField(
        choices=ComplianceStatusChoices.choices,
        max_length=50,
        default=ComplianceStatusChoices.PENDING,
    )
    company_type = models.CharField(
        null=True,
        blank=True,
        choices=CompanyType.choices,
        default=CompanyType.PRIVATE_LIMITED,
    )
    assignee = models.CharField(max_length=255, null=True, blank=True)
    last_filed_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    reminder_days = models.IntegerField(default=0)
    penalty_amount = models.CharField(
        null=True, blank=True, choices=PenaltyAmount.choices
    )
    payment_amount = models.CharField(max_length=100, null=True, blank=True)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    consequences = models.TextField(
        null=True,
        blank=True,
        choices=ConsequencesType.choices,
    )
    notes = models.TextField(null=True, blank=True)
    evidence_url = models.FileField(
        null=True,
        blank=True,
        upload_to="evidence_docs/",
        validators=[FileExtensionValidator(["pdf"])],
    )
    days_until_due = models.IntegerField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)
    interest_percentage = models.CharField(
        max_length=100, null=True, blank=True, choices=InterestType.choices
    )
    penalty = models.CharField(max_length=100, null=True, blank=True)
    late_fee = models.CharField(max_length=100, null=True, blank=True)
    interest_amount = models.CharField(max_length=100, null=True, blank=True)
    task_id = models.CharField(max_length=100, unique=True)
    is_admin_created = models.BooleanField(
        default=False,
        help_text="Mark true if created by superadmin; task is visible to all companies.",
    )
    companies = models.ManyToManyField(
        Company,
        related_name="selected_compliance_tasks",
        blank=True,
        help_text="Companies that have selected this task. Only selected tasks are displayed for each company.",
    )

    def calculate_days_until_due(self):
        """Calculate days until due date from today."""
        if not self.due_date:
            return None
        today = timezone.now().date()
        delta = (self.due_date - today).days
        return delta

    def calculate_is_overdue(self):
        """Check if task is overdue (due date passed and status not completed)."""
        if not self.due_date:
            return False
        today = timezone.now().date()
        is_past_due = self.due_date < today
        return is_past_due and self.status != ComplianceStatusChoices.COMPLETED

    def calculate_status(self):
        """Automatically calculate status based on dates and completion."""
        # If completed_date is set, status is COMPLETED
        if self.completed_date:
            return ComplianceStatusChoices.COMPLETED

        # If due_date has passed and not completed, status is OVERDUE
        if self.due_date:
            today = timezone.now().date()
            if self.due_date < today:
                return ComplianceStatusChoices.OVERDUE

        # If due_date is today or in the future, mark as IN_PROGRESS, else default to PENDING
        if self.due_date:
            today = timezone.now().date()
            if self.due_date == today:
                return ComplianceStatusChoices.IN_PROGRESS

        return ComplianceStatusChoices.PENDING

    def _add_months(self, base_date, months):
        """Utility to shift a date by a number of months."""
        month = base_date.month - 1 + months
        year = base_date.year + month // 12
        month = month % 12 + 1
        day = min(base_date.day, monthrange(year, month)[1])
        return date(year, month, day)

    def calculate_next_due_date(self):
        """Calculate next due date using due_date and frequency."""
        if not self.due_date or not self.frequency:
            return None

        base_date = self.due_date
        frequency_value = self.frequency

        monthly_frequencies = {
            Frequency.EVERY_MONTH_APRIL_MARCH,
            Frequency.MONTHLY_STATUTORY,
            Frequency.MONTHLY_PF_ESI,
            Frequency.MONTHLY_QUARTERLY_TDS,
        }
        quarterly_frequencies = {
            Frequency.QUARTERLY,
            Frequency.QUARTERLY_END,
            Frequency.QUARTERLY_TDS,
        }
        half_yearly_frequencies = {Frequency.HALF_YEARLY}
        annual_frequencies = {Frequency.ANNUALLY, Frequency.ANNUAL}
        non_periodic_frequencies = {
            Frequency.EVENT_BASED,
            Frequency.EVENT_BASED_AS_REQUIRED,
            Frequency.CONTINUOUS,
        }

        if frequency_value in monthly_frequencies:
            return self._add_months(base_date, 1)
        if frequency_value in quarterly_frequencies:
            return self._add_months(base_date, 3)
        if frequency_value in half_yearly_frequencies:
            return self._add_months(base_date, 6)
        if frequency_value in annual_frequencies:
            return self._add_months(base_date, 12)
        if frequency_value in non_periodic_frequencies:
            return None

        frequency_lower = frequency_value.lower()

        if frequency_lower == "monthly":
            return self._add_months(base_date, 1)
        if frequency_lower == "quarterly":
            return self._add_months(base_date, 3)
        if frequency_lower in {"half-yearly", "half yearly", "semi-annual"}:
            return self._add_months(base_date, 6)
        if frequency_lower in {"annually", "annual", "yearly"}:
            return self._add_months(base_date, 12)

        # Fall back to day-based frequency detection (e.g., "30 days")
        try:
            import re

            numbers = re.findall(r"\d+", frequency_lower)
            if numbers:
                days = int(numbers[0])
                return base_date + timedelta(days=days)
        except (ValueError, IndexError):
            return None

        return None

    def calculate_reminder_days(self):
        """Calculate reminder days as max(due_date - today, 0)."""
        if not self.due_date:
            return 0
        today = timezone.now().date()
        return max((self.due_date - today).days, 0)

    DATE_INPUT_FORMAT = "%d-%m-%Y"

    def _normalize_date_field(self, value, field_name):
        """Ensure date fields accept strings in DD-MM-YYYY format."""
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, self.DATE_INPUT_FORMAT).date()
            except ValueError as exc:
                raise ValidationError(
                    {field_name: "Use DD-MM-YYYY format (e.g., 25-11-2025)."}
                ) from exc
        raise ValidationError({field_name: "Provide a valid date value."})

    def clean(self):
        """Custom validation rules."""
        date_fields = [
            "due_date",
            "last_filed_date",
            "next_due_date",
            "completed_date",
        ]
        for field_name in date_fields:
            value = getattr(self, field_name)
            if value not in (None, ""):
                setattr(self, field_name, self._normalize_date_field(value, field_name))

        super().clean()
        if self.completed_date and self.status != ComplianceStatusChoices.COMPLETED:
            raise ValidationError(
                {
                    "completed_date": "Set status to COMPLETED before adding a completion date."
                }
            )
        if self.completed_date:
            today = timezone.now().date()
            if self.completed_date > today:
                raise ValidationError(
                    {"completed_date": "Completion date cannot be in the future."}
                )

    def _generate_task_id(self):
        """Auto-generate a task id using the act prefix."""
        act_value = self.act or "GEN"
        act_clean = (
            act_value.replace("Act", "")
            .replace("ACT", "")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .strip()
        )
        words = act_clean.split()
        if words:
            if len(words[0]) >= 3:
                act_prefix = words[0][:3].upper()
            else:
                act_prefix = "".join([w[0] for w in words[:3]])[:3].upper()
        else:
            act_prefix = act_value[:3].upper() if act_value else "GEN"

        existing_tasks = ComplianceTaskMaster.objects.filter(
            task_id__startswith=f"{act_prefix}-"
        )

        if existing_tasks.exists():
            max_num = 0
            for task in existing_tasks:
                try:
                    num_part = task.task_id.split("-")[1]
                    num = int(num_part)
                    if num > max_num:
                        max_num = num
                except (IndexError, ValueError):
                    continue
            next_num = max_num + 1
        else:
            next_num = 1

        return f"{act_prefix}-{str(next_num).zfill(3)}"

    def save(self, *args, **kwargs):
        original_task_id = None
        if self.pk:
            original_task_id = (
                ComplianceTaskMaster.objects.filter(pk=self.pk)
                .values_list("task_id", flat=True)
                .first()
            )

        manual_task_id_allowed = bool(self.is_admin_created and self.task_id)
        if not manual_task_id_allowed:
            if original_task_id:
                self.task_id = original_task_id
            else:
                self.task_id = None

        if not self.task_id:
            self.task_id = self._generate_task_id()

        # If completed_date is set, automatically set status to COMPLETED before validation
        # This ensures validation passes since clean() checks that status is COMPLETED when completed_date exists
        if self.completed_date:
            self.status = ComplianceStatusChoices.COMPLETED

        # Validate user-supplied data (e.g., completed_date vs status)
        self.full_clean(validate_unique=False)

        # Automatically calculate fields
        self.reminder_days = self.calculate_reminder_days()
        self.days_until_due = self.calculate_days_until_due()
        calculated_next_due = self.calculate_next_due_date()
        self.next_due_date = calculated_next_due

        # If status wasn't set above (no completed_date), calculate it
        if not self.completed_date:
            self.status = self.calculate_status()

        self.is_overdue = self.calculate_is_overdue()

        super().save(*args, **kwargs)

    class Meta:
        db_table = "compliance_task_master"
        verbose_name = "Compliance Task Master"
        verbose_name_plural = "Compliance Task Masters"

    def __str__(self):
        return f"{self.task_id} - {self.act}"


class CompliancePayments(BaseModel):
    compliance_task = models.ForeignKey(
        ComplianceTaskMaster,
        on_delete=models.CASCADE,
        related_name="compliance_payments",
        null=True,
        blank=True,
    )
    task_id = models.CharField(max_length=100, null=True, blank=True)
    payment_id = models.CharField(max_length=100, unique=True, editable=False)
    payment_type = models.CharField(max_length=100)
    period = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateField()
    amount = models.CharField(max_length=100)
    reference_number = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    related_act = models.CharField(max_length=255, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    days_early_or_late = models.IntegerField(null=True, blank=True)
    is_late = models.BooleanField(default=False)

    # Financial fields for exposure analysis
    estimated_penalty = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, default=0
    )
    estimated_interest = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, default=0
    )
    estimated_late_fee = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, default=0
    )

    def calculate_due_date(self):
        """Calculate due date from the compliance task."""
        if not self.compliance_task:
            return None
        # Use the task's due_date or next_due_date
        return self.compliance_task.due_date or self.compliance_task.next_due_date

    def calculate_days_early_or_late(self):
        """Calculate days early or late based on payment_date and due_date."""
        if not self.payment_date or not self.due_date:
            return None

        delta = (self.payment_date - self.due_date).days
        return delta  # Positive = late, Negative = early, 0 = on time

    def calculate_is_late(self):
        """Check if payment is late."""
        if not self.payment_date or not self.due_date:
            return False
        return self.payment_date > self.due_date

    def save(self, *args, **kwargs):
        if not self.payment_id:
            existing_payments = CompliancePayments.objects.filter(
                payment_id__startswith="PAY-"
            )

            if existing_payments.exists():
                max_num = 0
                for payment in existing_payments:
                    try:
                        num_part = payment.payment_id.split("-")[1]
                        num = int(num_part)
                        if num > max_num:
                            max_num = num
                    except (IndexError, ValueError):
                        continue
                next_num = max_num + 1
            else:
                next_num = 1

            self.payment_id = f"PAY-{str(next_num).zfill(3)}"

        # Automatically populate from compliance_task
        if self.compliance_task:
            if not self.task_id:
                self.task_id = self.compliance_task.task_id
            if not self.related_act:
                self.related_act = self.compliance_task.act

            # Calculate due_date from task if not provided
            if not self.due_date:
                self.due_date = self.calculate_due_date()

        # Calculate days_early_or_late
        if self.payment_date and self.due_date:
            self.days_early_or_late = self.calculate_days_early_or_late()
            self.is_late = self.calculate_is_late()

        super().save(*args, **kwargs)

    class Meta:
        db_table = "compliance_payments"
        verbose_name = "Compliance Payment"
        verbose_name_plural = "Compliance Payments"

    def __str__(self):
        return f"{self.payment_id} - {self.amount}"
