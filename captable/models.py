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
