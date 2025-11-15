from datetime import timedelta, date
from django.db import models
from django.utils import timezone

from backend.enums import ActNameChoices, ComplianceStatusChoices
from backend.models import BaseModel


# Create your models here.
class ComplianceTaskMaster(BaseModel):
    act = models.CharField(
        max_length=255,
        choices=ActNameChoices.choices,
    )
    particulars = models.TextField()
    due_date = models.DateField()
    frequency = models.CharField(max_length=100)
    severity = models.CharField(max_length=50)
    status = models.CharField(
        choices=ComplianceStatusChoices.choices,
        max_length=50,
        default=ComplianceStatusChoices.PENDING,
    )
    company_type = models.CharField(max_length=100, null=True, blank=True)
    assignee = models.CharField(max_length=255, null=True, blank=True)
    last_filed_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    reminder_days = models.IntegerField(default=0)
    penalty_amount = models.CharField(max_length=100, null=True, blank=True)
    payment_amount = models.CharField(max_length=100, null=True, blank=True)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    consequences = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    evidence_url = models.URLField(null=True, blank=True)
    days_until_due = models.IntegerField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)
    interest_percentage = models.CharField(max_length=100, null=True, blank=True)
    penalty = models.CharField(max_length=100, null=True, blank=True)
    late_fee = models.CharField(max_length=100, null=True, blank=True)
    interest_amount = models.CharField(max_length=100, null=True, blank=True)
    task_id = models.CharField(max_length=100, unique=True, editable=False)

    def calculate_days_until_due(self):
        """Calculate days until due date from today."""
        if not self.due_date:
            return None
        today = timezone.now().date()
        delta = (self.due_date - today).days
        return delta

    def calculate_is_overdue(self):
        """Check if task is overdue (due date passed and not completed)."""
        if not self.due_date:
            return False
        today = timezone.now().date()
        is_past_due = self.due_date < today
        # Check if completed_date is set (more reliable than checking status)
        is_not_completed = not self.completed_date
        return is_past_due and is_not_completed

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

        # If due_date is today or in the future, check if it's within reminder days
        # If within reminder period, status could be AUTO (for automatic reminders)
        if self.due_date:
            today = timezone.now().date()
            days_until = (self.due_date - today).days
            if 0 <= days_until <= self.reminder_days:
                return ComplianceStatusChoices.AUTO

        # Default to PENDING
        return ComplianceStatusChoices.PENDING

    def calculate_next_due_date(self):
        """Calculate next due date based on frequency and last_filed_date or due_date."""
        if not self.frequency:
            return None

        # Use last_filed_date if available, otherwise use due_date
        base_date = self.last_filed_date if self.last_filed_date else self.due_date
        if not base_date:
            return None

        frequency_lower = self.frequency.lower()

        # Parse frequency (e.g., "Monthly", "Quarterly", "Annually", "30 days", etc.)
        if "daily" in frequency_lower or frequency_lower == "daily":
            return base_date + timedelta(days=1)
        elif "weekly" in frequency_lower or frequency_lower == "weekly":
            return base_date + timedelta(weeks=1)
        elif "monthly" in frequency_lower or frequency_lower == "monthly":
            # Add 1 month manually, handling edge cases
            new_month = base_date.month + 1
            new_year = base_date.year
            if new_month > 12:
                new_year += 1
                new_month = 1
            # Handle day overflow (e.g., Jan 31 -> Feb 28/29)
            try:
                return date(new_year, new_month, base_date.day)
            except ValueError:
                # If day doesn't exist in target month, use last day of month
                from calendar import monthrange

                last_day = monthrange(new_year, new_month)[1]
                return date(new_year, new_month, last_day)
        elif "quarterly" in frequency_lower or frequency_lower == "quarterly":
            # Add 3 months manually
            new_month = base_date.month + 3
            new_year = base_date.year
            if new_month > 12:
                new_year += 1
                new_month -= 12
            # Handle day overflow
            try:
                return date(new_year, new_month, base_date.day)
            except ValueError:
                from calendar import monthrange

                last_day = monthrange(new_year, new_month)[1]
                return date(new_year, new_month, last_day)
        elif (
            "half-yearly" in frequency_lower
            or "half yearly" in frequency_lower
            or "semi-annual" in frequency_lower
        ):
            # Add 6 months manually
            new_month = base_date.month + 6
            new_year = base_date.year
            if new_month > 12:
                new_year += 1
                new_month -= 12
            # Handle day overflow
            try:
                return date(new_year, new_month, base_date.day)
            except ValueError:
                from calendar import monthrange

                last_day = monthrange(new_year, new_month)[1]
                return date(new_year, new_month, last_day)
        elif (
            "annually" in frequency_lower
            or "annual" in frequency_lower
            or "yearly" in frequency_lower
        ):
            # Add 1 year manually, handle leap year edge case (Feb 29)
            try:
                return date(base_date.year + 1, base_date.month, base_date.day)
            except ValueError:
                # Handle Feb 29 -> Feb 28 in non-leap year
                from calendar import monthrange

                last_day = monthrange(base_date.year + 1, base_date.month)[1]
                return date(base_date.year + 1, base_date.month, last_day)
        else:
            # Try to extract number of days from frequency string
            try:
                # Look for patterns like "30 days", "90 days", etc.
                import re

                numbers = re.findall(r"\d+", frequency_lower)
                if numbers:
                    days = int(numbers[0])
                    return base_date + timedelta(days=days)
            except (ValueError, IndexError):
                pass

        # Default: if frequency is not recognized, return None
        return None

    def calculate_reminder_days(self):
        """Calculate reminder days based on frequency or set a default."""
        if self.reminder_days and self.reminder_days > 0:
            return self.reminder_days

        # Default reminder days based on frequency
        if not self.frequency:
            return 7  # Default 7 days

        frequency_lower = self.frequency.lower()

        if "daily" in frequency_lower:
            return 0  # No reminder needed for daily tasks
        elif "weekly" in frequency_lower:
            return 1  # 1 day before (remind on day 6 of 7)
        elif "monthly" in frequency_lower:
            return 7  # 7 days before (1 week notice)
        elif "quarterly" in frequency_lower:
            return 14  # 14 days before (2 weeks notice)
        elif "half-yearly" in frequency_lower or "half yearly" in frequency_lower:
            return 30  # 30 days before (1 month notice)
        elif (
            "annually" in frequency_lower
            or "annual" in frequency_lower
            or "yearly" in frequency_lower
        ):
            return 60  # 60 days before (2 months notice for annual tasks)
        else:
            # Try to extract number of days from frequency string and calculate percentage
            try:
                import re

                numbers = re.findall(r"\d+", frequency_lower)
                if numbers:
                    days = int(numbers[0])
                    # Calculate reminder as 10% of the period, minimum 1 day, maximum 60 days
                    reminder = max(1, min(60, int(days * 0.1)))
                    return reminder
            except (ValueError, IndexError):
                pass

            return 7  # Default 7 days for unrecognized frequencies

    def save(self, *args, **kwargs):
        if not self.task_id:
            # Get first 3 characters of act value (not label), uppercase
            # Act is stored as the choice value (e.g., "Companies Act, 2013")
            # Extract meaningful prefix - take first 3 letters, skipping common words
            act_value = self.act

            # Handle different act formats
            # For "Companies Act, 2013" -> "COM"
            # For "FEMA" -> "FEM"
            # For "LLP Act 2008" -> "LLP"
            # For "CGST ACT 2017" -> "CGS"
            # For "Income Tax Act, 1961" -> "INC"
            # For "ESI Act 1948" -> "ESI"
            # For "EPF Act 1952" -> "EPF"
            # For "SEBI (LODR)" -> "SEB"
            # For "SEBI" -> "SEB"
            # For "MSME Act" -> "MSM"

            # Remove common words and get first 3 meaningful characters
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
                # Take first word, or combine first letters
                if len(words[0]) >= 3:
                    act_prefix = words[0][:3].upper()
                else:
                    # Combine first letters of first two words if needed
                    act_prefix = "".join([w[0] for w in words[:3]])[:3].upper()
            else:
                act_prefix = act_value[:3].upper()

            # Find the highest number for this act prefix
            existing_tasks = ComplianceTaskMaster.objects.filter(
                task_id__startswith=f"{act_prefix}-"
            )

            if existing_tasks.exists():
                # Extract numbers from existing task_ids
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

            self.task_id = f"{act_prefix}-{str(next_num).zfill(3)}"

        # Automatically calculate fields
        # Calculate reminder_days if not set
        if not self.reminder_days or self.reminder_days == 0:
            self.reminder_days = self.calculate_reminder_days()

        # Calculate days_until_due
        self.days_until_due = self.calculate_days_until_due()

        # Calculate status automatically (unless explicitly set to COMPLETED with completed_date)
        # Do this before is_overdue calculation
        if self.completed_date:
            self.status = ComplianceStatusChoices.COMPLETED
        else:
            self.status = self.calculate_status()

        # Calculate is_overdue (after status is set)
        self.is_overdue = self.calculate_is_overdue()

        # Calculate next_due_date if not set or if last_filed_date changed
        if not self.next_due_date or self.last_filed_date:
            calculated_next_due = self.calculate_next_due_date()
            if calculated_next_due:
                self.next_due_date = calculated_next_due

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
