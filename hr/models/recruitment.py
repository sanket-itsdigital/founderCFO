from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator

from accounts.models import Company
from backend.models import BaseModel
from hr.models.department import Department


class RecruitmentStatusChoices(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in progress", "In Progress"
    FILLED = "filled", "Filled"


class RecruitmentSourceChoices(models.TextChoices):
    COMPANY_WEBSITE = "Company Website", "Company Website"
    CAMPUS_HIRING = "Campus Hiring", "Campus Hiring"
    LINKEDIN = "LinkedIn", "LinkedIn"
    NAUKRI = "Naukri", "Naukri"
    EMPLOYEE_REFERRAL = "Employee Referral", "Employee Referral"
    AGENCY = "Agency", "Agency"
    JOB_BOARD = "Job Board", "Job Board"
    OTHER = "Other", "Other"


class Recruitment(BaseModel):
    """HR Recruitment model for tracking job openings and hiring process"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="recruitments",
    )
    job_title = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recruitments",
    )
    status = models.CharField(
        max_length=50,
        choices=RecruitmentStatusChoices.choices,
        default=RecruitmentStatusChoices.OPEN,
    )
    positions_required = models.PositiveIntegerField(default=1)
    applications_received = models.PositiveIntegerField(default=0)
    interviews_conducted = models.PositiveIntegerField(default=0)
    offers_made = models.PositiveIntegerField(default=0)
    offers_accepted = models.PositiveIntegerField(default=0)
    cost_spent = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    source = models.CharField(
        max_length=100,
        choices=RecruitmentSourceChoices.choices,
        blank=True,
        null=True,
    )
    posting_date = models.DateField()
    target_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)
    salary_range_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    salary_range_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        db_table = "recruitment"
        verbose_name = "Recruitment"
        verbose_name_plural = "Recruitments"
        ordering = ["-posting_date"]

    def __str__(self):
        return f"{self.job_title} - {self.department.name if self.department else 'No Department'}"

    @property
    def time_to_hire_days(self):
        """Calculate time to hire in days"""
        if self.actual_close_date and self.posting_date:
            return (self.actual_close_date - self.posting_date).days
        return None

    @property
    def cost_per_hire(self):
        """Calculate cost per hire"""
        if self.offers_accepted > 0:
            return self.cost_spent / Decimal(str(self.offers_accepted))
        return Decimal("0.00")

    @property
    def conversion_rate(self):
        """Calculate conversion rate from applications to hires"""
        if self.applications_received > 0:
            return (
                Decimal(str(self.offers_accepted))
                / Decimal(str(self.applications_received))
            ) * Decimal("100")
        return Decimal("0.00")
