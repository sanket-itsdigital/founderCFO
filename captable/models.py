from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from backend.models import BaseModel
from captable.enums import (
    CapTableEventStatus,
    ESOPGrantStatus,
    ESOPGrantType,
    InvestorType,
    ShareClassType,
    VestingFrequency,
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
        ordering = ["date"]

    def clean(self):
        """Validate that only one event of each type exists per company (except Founders' Equity and ESOP Grant).
        Also validate that INCORPORATION events have at least 2 founders."""
        super().clean()

        # Event types that can only have one instance per company
        SINGLE_INSTANCE_EVENTS = [
            CapTableEventStatus.INCORPORATION,
            CapTableEventStatus.SEED_ROUND,
            CapTableEventStatus.SERIES_A,
            CapTableEventStatus.SERIES_B,
            CapTableEventStatus.SERIES_C,
            CapTableEventStatus.SERIES_D,
            CapTableEventStatus.SECONDARY_SALE,
        ]

        # Founders' Equity and ESOP Grant can have multiple instances
        MULTIPLE_INSTANCE_EVENTS = [
            CapTableEventStatus.FOUNDERS_EQUITY,
            CapTableEventStatus.ESOP_GRANT,
        ]

        if not self.company_id:
            return

        # Define the sequential order of events - each event requires ALL previous events
        EVENT_SEQUENCE = [
            CapTableEventStatus.INCORPORATION,  # First event, no prerequisite
            CapTableEventStatus.SEED_ROUND,  # Requires Incorporation
            CapTableEventStatus.SERIES_A,  # Requires Incorporation, Seed Round
            CapTableEventStatus.SERIES_B,  # Requires Incorporation, Seed Round, Series A
            CapTableEventStatus.SERIES_C,  # Requires Incorporation, Seed Round, Series A, Series B
            CapTableEventStatus.SERIES_D,  # Requires Incorporation, Seed Round, Series A, Series B, Series C
        ]

        # Validate sequential order - check if ALL previous events exist
        if self.event_type in EVENT_SEQUENCE:
            event_index = EVENT_SEQUENCE.index(self.event_type)

            # If not the first event (Incorporation), check all previous events
            if event_index > 0:
                required_events = EVENT_SEQUENCE[:event_index]
                missing_events = []

                for required_event in required_events:
                    event_exists = CapTableEvents.objects.filter(
                        company=self.company, event_type=required_event
                    ).exists()

                    if not event_exists:
                        event_display = dict(CapTableEventStatus.choices).get(
                            required_event, required_event
                        )
                        missing_events.append(event_display)

                if missing_events:
                    current_event_display = self.get_event_type_display()
                    missing_events_str = ", ".join(missing_events)
                    sequence_str = " → ".join(
                        [
                            dict(CapTableEventStatus.choices).get(evt, evt)
                            for evt in EVENT_SEQUENCE
                        ]
                    )

                    raise ValidationError(
                        {
                            "event_type": f"To create a '{current_event_display}' event, "
                            f"you must first create the following missing event(s): {missing_events_str}. "
                            f"Please create all events in the correct sequence: {sequence_str}"
                        }
                    )

        if self.event_type in SINGLE_INSTANCE_EVENTS:
            # Check if another event of the same type exists for this company
            existing_events = CapTableEvents.objects.filter(
                company=self.company, event_type=self.event_type
            )

            # Exclude current instance if updating
            if self.pk:
                existing_events = existing_events.exclude(pk=self.pk)

            if existing_events.exists():
                raise ValidationError(
                    {
                        "event_type": f"An event of type '{self.get_event_type_display()}' already exists for this company. "
                        f"Only one instance of this event type is allowed."
                    }
                )

        # Validate that INCORPORATION events have at least 2 founders and all shareholders are founders
        # Note: For new events (no pk), skip this validation as it's handled by serializers when transactions are created
        # This validation only runs for existing events being updated
        if self.event_type == CapTableEventStatus.INCORPORATION:
            # Skip validation for new events (no primary key yet)
            if not self.pk:
                return

            # For existing events, check transactions
            all_transactions = self.transactions.select_related("shareholder").all()

            # Skip validation if no transactions exist yet (event just created, transactions will be added)
            if not all_transactions.exists():
                return

            # Check that all shareholders are founders
            non_founder_transactions = [
                tx
                for tx in all_transactions
                if tx.shareholder.investor_type != InvestorType.FOUNDER
            ]

            if non_founder_transactions:
                non_founder_names = [
                    tx.shareholder.name for tx in non_founder_transactions
                ]
                raise ValidationError(
                    {
                        "event_type": f"For INCORPORATION events, all shareholders must have investor_type='Founder'. "
                        f"Found shareholders with other investor types: {', '.join(non_founder_names)}"
                    }
                )

            founder_transactions = (
                self.transactions.filter(
                    shareholder__investor_type=InvestorType.FOUNDER
                )
                .values_list("shareholder_id", flat=True)
                .distinct()
            )

            founder_count = len(founder_transactions)

            if founder_count < 2:
                raise ValidationError(
                    {
                        "event_type": f"An INCORPORATION event requires at least 2 founders. "
                        f"Currently, this event has {founder_count} founder(s). "
                        f"Please add transactions with at least 2 founders before saving."
                    }
                )


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
        ordering = ["event__date"]


class VestingSchedule(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="vesting_schedules",
    )
    name = models.CharField(max_length=255)
    total_shares = models.PositiveIntegerField()
    start_date = models.DateField()
    vesting_frequency = models.CharField(
        max_length=20,
        choices=VestingFrequency.choices,
        default=VestingFrequency.MONTHLY,
    )
    cliff_period_months = models.PositiveIntegerField()
    total_vesting_period_months = models.PositiveIntegerField()
    single_trigger = models.BooleanField(default=False)
    double_trigger = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "captable_vesting_schedule"
        verbose_name = "Vesting Schedule"
        verbose_name_plural = "Vesting Schedules"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_vesting_schedule_per_company",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.company_id})"

    def clean(self):
        super().clean()
        if (
            self.total_vesting_period_months
            and self.cliff_period_months
            and self.total_vesting_period_months < self.cliff_period_months
        ):
            raise ValidationError(
                {"total_vesting_period_months": "Total period must exceed cliff."}
            )


def validate_not_future(value):
    if value > timezone.now().date():
        raise ValidationError("Grant date cannot be in the future.")


def validate_future_only(value):
    if value <= timezone.now().date():
        raise ValidationError("Cliff date must be in the future.")


class ESOPGrant(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="esop_grants",
    )
    employee_name = models.CharField(max_length=255)
    employee_email = models.EmailField()
    grant_date = models.DateField(validators=[validate_not_future])
    cliff_date = models.DateField(validators=[validate_future_only])
    total_options = models.PositiveIntegerField()
    strike_price = models.DecimalField(max_digits=12, decimal_places=2)
    fair_market_value = models.DecimalField(max_digits=12, decimal_places=2)
    exercise_window_days = models.PositiveIntegerField()
    vesting_schedule = models.TextField()
    vesting_schedule_plan = models.ForeignKey(
        "VestingSchedule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="esop_grants",
    )
    grant_type = models.CharField(
        max_length=20,
        choices=ESOPGrantType.choices,
        default=ESOPGrantType.STOCK_OPTIONS,
    )
    status = models.CharField(
        max_length=20,
        choices=ESOPGrantStatus.choices,
        default=ESOPGrantStatus.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "captable_esop_grant"
        verbose_name = "ESOP Grant"
        verbose_name_plural = "ESOP Grants"
        ordering = ["-grant_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "employee_email", "grant_date"],
                name="unique_esop_per_employee_per_company_per_grant_date",
            )
        ]

    def __str__(self):
        return f"{self.employee_name} - {self.grant_type}"

    def clean(self):
        super().clean()
        validate_not_future(self.grant_date)
        validate_future_only(self.cliff_date)

    def _months_between(self, start_date, end_date):
        if not start_date or not end_date or end_date < start_date:
            return 0
        years = end_date.year - start_date.year
        months = end_date.month - start_date.month
        total_months = years * 12 + months
        if end_date.day >= start_date.day:
            total_months += 1
        return total_months

    def calculate_vesting_metrics(self, reference_date=None):
        """
        Calculate current vesting metrics for the grant.

        Args:
            reference_date (date, optional): Date to use for the calculation.
                Defaults to today's date if omitted.

        Returns:
            tuple[Decimal, Decimal, Decimal]: A tuple containing
                (progress_percent, vested_options, unvested_options).

        Example:
            >>> progress, vested, unvested = grant.calculate_vesting_metrics()
            >>> progress
            Decimal('45.8')
        """
        total_options = Decimal(self.total_options or 0)
        if total_options <= 0:
            return Decimal("0"), Decimal("0"), Decimal("0")

        plan = self.vesting_schedule_plan
        if not plan or not plan.start_date or not plan.total_vesting_period_months:
            return Decimal("0"), Decimal("0"), total_options

        reference_date = reference_date or timezone.now().date()
        total_period = plan.total_vesting_period_months
        elapsed_months = min(
            total_period,
            self._months_between(plan.start_date, reference_date),
        )
        if elapsed_months < plan.cliff_period_months:
            vested_ratio = Decimal("0")
        else:
            vested_ratio = Decimal(elapsed_months) / Decimal(total_period)
        vested_ratio = min(vested_ratio, Decimal("1"))

        vested_options = (total_options * vested_ratio).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        unvested_options = total_options - vested_options
        progress_percent = (
            (vested_options / total_options) * Decimal("100")
            if total_options
            else Decimal("0")
        )
        progress_percent = progress_percent.quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        return progress_percent, vested_options, unvested_options


class ESOPPoolHistory(BaseModel):
    """Track ESOP pool changes over time."""

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="esop_pool_history",
    )
    event_type = models.CharField(
        max_length=50,
        choices=[
            ("POOL_CREATED", "Pool Created"),
            ("POOL_EXPANDED", "Pool Expanded"),
            ("POOL_REDUCED", "Pool Reduced"),
        ],
        default="POOL_CREATED",
    )
    event_date = models.DateField()
    pool_size_before = models.PositiveIntegerField(default=0)
    pool_size_after = models.PositiveIntegerField(default=0)
    pool_percentage_before = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    pool_percentage_after = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    change_amount = models.IntegerField(
        help_text="Change in pool size (positive for increase, negative for decrease)"
    )
    description = models.TextField(blank=True, help_text="Description of the change")
    notes = models.TextField(
        blank=True, null=True, help_text="Additional notes about the change"
    )

    class Meta:
        db_table = "captable_esop_pool_history"
        verbose_name = "ESOP Pool History"
        verbose_name_plural = "ESOP Pool Histories"
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.company.name} - {self.event_type} on {self.event_date}"

    def save(self, *args, **kwargs):
        """Calculate change_amount if not provided."""
        if not hasattr(self, "_change_calculated"):
            self.change_amount = self.pool_size_after - self.pool_size_before
            self._change_calculated = True
        super().save(*args, **kwargs)
