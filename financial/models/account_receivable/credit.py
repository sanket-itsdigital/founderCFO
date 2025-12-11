from decimal import Decimal

from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import RiskLevelChoices


class Credit(BaseModel):
    """Customer credit limit and payment history"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="credits",
    )
    customer_name = models.CharField(max_length=255)
    credit_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("500000.00"),  # Default 5 lakh
        help_text="Maximum credit limit extended to the customer (editable)",
    )
    payment_score = models.IntegerField(
        default=0,
        help_text="Payment score out of 100 (calculated from payment history)",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevelChoices.choices,
        default=RiskLevelChoices.LOW,
        help_text="Risk level based on payment behavior and utilization",
    )
    avg_days_to_pay = models.IntegerField(
        default=0,
        help_text="Average number of days taken to pay invoices",
    )

    class Meta:
        db_table = "credit"
        verbose_name = "Credit"
        verbose_name_plural = "Credits"
        ordering = ["customer_name"]
        unique_together = ["company", "customer_name"]

    def __str__(self):
        return f"{self.customer_name} - {self.company.name}"

    @property
    def current_balance(self):
        """Calculate current outstanding balance from invoices"""
        from revenue.models.invoice import Invoice
        from financial.enums import InvoicesStatusChoices
        from django.db.models import Sum, F

        outstanding = Invoice.objects.filter(
            company=self.company, customer_name=self.customer_name
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).aggregate(
            total=Sum(F("total_amount") - F("paid_amount"))
        )[
            "total"
        ] or Decimal(
            "0.00"
        )

        return outstanding

    @property
    def utilization_percentage(self):
        """Calculate credit utilization percentage"""
        if self.credit_limit == 0:
            return 0
        return float((self.current_balance / self.credit_limit) * 100)

    def get_risk_level_display(self):
        """Get risk level display value"""
        return dict(RiskLevelChoices.choices).get(self.risk_level, self.risk_level)
