from backend.models import BaseModel
from django.db import models

from hr.enums import EmploymentStatus, EmploymentType, Gender, Level


class Headcount(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="headcounts",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        related_name="headcounts",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        "Role",
        on_delete=models.SET_NULL,
        related_name="headcounts",
        null=True,
        blank=True,
    )
    level = models.CharField(
        max_length=50,
        choices=Level.choices,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=50,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    employment = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    gender = models.CharField(
        max_length=50,
        choices=Gender.choices,
        default=Gender.MALE,
    )
    location = models.CharField(max_length=255, null=True, blank=True)
    salary_annual = models.DecimalField(max_digits=12, decimal_places=2)
    benefits_annual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    bouns_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )  # e.g., 10.00 for 10%
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    exit_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "headcount"
        verbose_name = "Headcount"
        verbose_name_plural = "Headcounts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"
