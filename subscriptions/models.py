from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel


class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_plan"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} ({self.duration_days} days)"


class CompanySubscription(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchased_subscriptions",
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "company_subscription"
        ordering = ["-end_date"]

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"

    @property
    def days_remaining(self) -> int:
        today = timezone.now().date()
        if self.end_date < today:
            return 0
        return (self.end_date - today).days

    @property
    def is_active(self) -> bool:
        return (
            self.status == self.Status.ACTIVE and self.end_date >= timezone.now().date()
        )

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        if self.end_date < today:
            self.status = self.Status.EXPIRED
        elif self.status != self.Status.CANCELLED:
            self.status = self.Status.ACTIVE
        super().save(*args, **kwargs)

    @classmethod
    def create_for_plan(cls, company, plan, purchased_by, start_date=None):
        start = start_date or timezone.now().date()
        end = start + timedelta(days=plan.duration_days)
        return cls.objects.create(
            company=company,
            plan=plan,
            purchased_by=purchased_by,
            amount_paid=plan.price,
            start_date=start,
            end_date=end,
        )
