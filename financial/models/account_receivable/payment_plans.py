from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import (
    PaymentPlanStatusChoices,
    PaymentFrequencyChoices,
    InstallmentStatusChoices,
)
from revenue.models.invoice import Invoice


class PaymentPlan(BaseModel):
    """Payment plans for invoices"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payment_plans",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payment_plans",
    )
    number_of_installments = models.IntegerField()
    payment_frequency = models.CharField(
        max_length=20,
        choices=PaymentFrequencyChoices.choices,
        default=PaymentFrequencyChoices.MONTHLY,
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentPlanStatusChoices.choices,
        default=PaymentPlanStatusChoices.ACTIVE,
    )
    start_date = models.DateField()

    class Meta:
        db_table = "payment_plan"
        verbose_name = "Payment Plan"
        verbose_name_plural = "Payment Plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment Plan for {self.invoice.invoice_number} - {self.get_status_display()}"

    @property
    def paid_amount(self):
        """Calculate total amount paid across all installments"""
        return self.installments.filter(status=InstallmentStatusChoices.PAID).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.total_amount - self.paid_amount

    @property
    def progress_percentage(self):
        """Calculate payment progress percentage"""
        if self.total_amount == 0:
            return 0.0
        return float((self.paid_amount / self.total_amount) * 100)

    def create_installments(self):
        """Create installments based on plan configuration"""

        # Clear existing installments if any
        self.installments.all().delete()

        installment_amount = self.total_amount / self.number_of_installments
        current_date = self.start_date

        for i in range(1, self.number_of_installments + 1):
            # Calculate due date based on frequency
            if self.payment_frequency == PaymentFrequencyChoices.WEEKLY:
                due_date = current_date + timedelta(weeks=i - 1)
            elif self.payment_frequency == PaymentFrequencyChoices.BI_WEEKLY:
                due_date = current_date + timedelta(weeks=(i - 1) * 2)
            elif self.payment_frequency == PaymentFrequencyChoices.MONTHLY:
                # Add months manually - handle month overflow
                month = current_date.month + (i - 1)
                year = current_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28/29)
                try:
                    due_date = current_date.replace(year=year, month=month)
                except ValueError:
                    # If day doesn't exist in target month, use last day of month
                    from calendar import monthrange

                    last_day = monthrange(year, month)[1]
                    due_date = current_date.replace(
                        year=year, month=month, day=min(current_date.day, last_day)
                    )
            elif self.payment_frequency == PaymentFrequencyChoices.QUARTERLY:
                # Add quarters (3 months)
                month = current_date.month + (i - 1) * 3
                year = current_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    due_date = current_date.replace(year=year, month=month)
                except ValueError:
                    from calendar import monthrange

                    last_day = monthrange(year, month)[1]
                    due_date = current_date.replace(
                        year=year, month=month, day=min(current_date.day, last_day)
                    )
            else:  # ANNUALLY
                try:
                    due_date = current_date.replace(year=current_date.year + (i - 1))
                except ValueError:
                    # Handle leap year edge case (Feb 29)
                    from calendar import monthrange

                    year = current_date.year + (i - 1)
                    last_day = monthrange(year, 2)[1]
                    due_date = current_date.replace(
                        year=year, day=min(current_date.day, last_day)
                    )

            # For last installment, add any rounding difference
            if i == self.number_of_installments:
                amount = self.total_amount - (
                    installment_amount * (self.number_of_installments - 1)
                )
            else:
                amount = installment_amount

            PaymentPlanInstallment.objects.create(
                payment_plan=self,
                installment_number=i,
                due_date=due_date,
                amount=amount,
                status=InstallmentStatusChoices.PENDING,
            )

    def mark_as_completed(self):
        """Mark plan as completed if all installments are paid"""
        if (
            self.installments.filter(status=InstallmentStatusChoices.PAID).count()
            == self.number_of_installments
        ):
            self.status = PaymentPlanStatusChoices.COMPLETED
            self.save(update_fields=["status"])


class PaymentPlanInstallment(BaseModel):
    """Individual installments for payment plans"""

    payment_plan = models.ForeignKey(
        PaymentPlan,
        on_delete=models.CASCADE,
        related_name="installments",
    )
    installment_number = models.IntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=InstallmentStatusChoices.choices,
        default=InstallmentStatusChoices.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "payment_plan_installment"
        verbose_name = "Payment Plan Installment"
        verbose_name_plural = "Payment Plan Installments"
        ordering = ["installment_number"]
        unique_together = ["payment_plan", "installment_number"]

    def __str__(self):
        return f"Installment {self.installment_number} - {self.payment_plan.invoice.invoice_number}"

    @property
    def is_overdue(self):
        """Check if installment is overdue"""
        return (
            self.due_date < timezone.now().date()
            and self.status == InstallmentStatusChoices.PENDING
        )

    def mark_as_paid(self, payment_reference=""):
        """Mark installment as paid"""
        self.status = InstallmentStatusChoices.PAID
        self.paid_at = timezone.now()
        self.payment_reference = payment_reference
        self.save(update_fields=["status", "paid_at", "payment_reference"])

        # Check if plan should be marked as completed
        self.payment_plan.mark_as_completed()
