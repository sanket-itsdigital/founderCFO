from decimal import Decimal

from django.db import models

from accounts.models import Company
from backend.models import BaseModel


class DiscountProgram(BaseModel):
    """Early payment discount programs"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="discount_programs",
        null=True,
        blank=True,
        help_text="If null, program is available to all companies"
    )
    program_name = models.CharField(
        max_length=100,
        help_text="e.g., 2/10 Net 30"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Discount percentage (e.g., 2 for 2%)"
    )
    discount_days = models.IntegerField(
        help_text="Number of days within which discount applies"
    )
    net_days = models.IntegerField(
        help_text="Total number of days until full payment is due"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discount_program"
        verbose_name = "Discount Program"
        verbose_name_plural = "Discount Programs"
        ordering = ["program_name"]

    def __str__(self):
        return f"{self.program_name} - {self.company.name if self.company else 'Global'}"

    @property
    def annualized_cost_of_not_taking(self):
        """Calculate annualized cost of not taking the discount"""
        if self.net_days <= self.discount_days:
            return 0.0
        
        discount_decimal = self.discount_percentage / 100
        days_difference = self.net_days - self.discount_days
        
        # Formula: (Discount % / (100 - Discount %)) * (365 / (Net Days - Discount Days))
        annualized_cost = (discount_decimal / (1 - discount_decimal)) * (365 / days_difference)
        return float(annualized_cost * 100)  # Return as percentage

    @property
    def description(self):
        """Generate description text"""
        return f"{self.discount_percentage}% off if paid within {self.discount_days} days, otherwise due in {self.net_days} days"

