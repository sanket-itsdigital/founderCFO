from decimal import Decimal

from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import OrderStatusChoices


class Order(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_number = models.CharField(max_length=50, unique=True)

    # Customer/Vendor Information
    customer_name = models.CharField(max_length=255)

    # Order Details
    order_date = models.DateField()
    delivery_date = models.DateField(blank=True, null=True)

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=OrderStatusChoices.choices,
        default=OrderStatusChoices.PENDING,
    )
    is_invoiced = models.BooleanField(default=False)

    class Meta:
        db_table = "order"
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-order_date"]
        unique_together = ["company", "order_number"]

    def __str__(self):
        return f"{self.order_number} - {self.customer_name}"

    @property
    def outstanding_amount(self):
        """Calculate outstanding amount for the order"""
        return self.total_amount

    @property
    def is_overdue(self):
        """Check if the order delivery is overdue"""
        from django.utils import timezone

        if self.delivery_date and self.status not in [
            OrderStatusChoices.DELIVERED,
            OrderStatusChoices.CANCELLED,
        ]:
            return self.delivery_date < timezone.now().date()
        return False

    def save(self, *args, **kwargs):
        """Save method - total_amount should be set manually"""
        super().save(*args, **kwargs)
