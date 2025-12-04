from django.db import models

from backend.models import BaseModel


class Balance_summary(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="balance_summaries",
    )
    customer_name = models.CharField(max_length=255)
    outstanding_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
    )
    credit_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
    )
    utilized_credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
    )
    invoice_count = models.IntegerField(default=0)
    average_days = models.IntegerField(default=0)

    class Meta:
        db_table = "balance_summary"
        verbose_name = "Balance Summary"
        verbose_name_plural = "Balance Summaries"
        ordering = ["customer_name"]

    def __str__(self):
        return f"{self.customer_name} - {self.company.name}"

    @property
    def credit_utilization_percentage(self):
        """Calculate credit utilization percentage"""
        if self.credit_limit == 0:
            return 0
        return (self.outstanding_amount / self.credit_limit) * 100
