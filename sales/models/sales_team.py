from django.db import models

from accounts.models import Company
from backend.models import BaseModel


class SalesTeam(BaseModel):
    """Sales Team Member model for managing sales representatives"""
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sales_teams",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    employee_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Employee ID or unique identifier",
    )
    designation = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Job title or designation",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the team member is currently active",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "sales_team"
        verbose_name = "Sales Team Member"
        verbose_name_plural = "Sales Team Members"
        ordering = ["name"]
        unique_together = ["company", "email"]

    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else ''}"

