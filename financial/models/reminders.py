from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import (
    ReminderStatusChoices,
    ReminderTriggerTypeChoices,
)
from financial.models.account_receivable import Invoice


class ReminderRule(BaseModel):
    """Automation rules for sending reminders"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="reminder_rules",
    )
    rule_name = models.CharField(max_length=255)
    trigger_days = models.IntegerField(
        help_text="Number of days before/after due date to trigger reminder"
    )
    trigger_type = models.CharField(
        max_length=50,
        choices=ReminderTriggerTypeChoices.choices,
        default=ReminderTriggerTypeChoices.BEFORE_DUE_DATE,
    )
    email_template_name = models.CharField(
        max_length=255,
        default="Friendly Reminder",
        help_text="Name of the email template to use"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "reminder_rule"
        verbose_name = "Reminder Rule"
        verbose_name_plural = "Reminder Rules"
        ordering = ["trigger_days"]

    def __str__(self):
        return f"{self.rule_name} - {self.company.name}"

    def calculate_scheduled_date(self, invoice_due_date):
        """Calculate when reminder should be sent based on rule"""
        if self.trigger_type == ReminderTriggerTypeChoices.BEFORE_DUE_DATE:
            return invoice_due_date - timedelta(days=self.trigger_days)
        elif self.trigger_type == ReminderTriggerTypeChoices.AFTER_DUE_DATE:
            return invoice_due_date + timedelta(days=self.trigger_days)
        else:  # ON_DUE_DATE
            return invoice_due_date


class Reminder(BaseModel):
    """Scheduled reminders for invoices"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    reminder_rule = models.ForeignKey(
        ReminderRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reminders",
    )
    scheduled_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ReminderStatusChoices.choices,
        default=ReminderStatusChoices.PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    email_template_name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "reminder"
        verbose_name = "Reminder"
        verbose_name_plural = "Reminders"
        ordering = ["scheduled_date", "invoice__due_date"]

    def __str__(self):
        return f"Reminder for {self.invoice.invoice_number} - {self.scheduled_date}"

    @property
    def is_due_today(self):
        """Check if reminder is due today"""
        return self.scheduled_date == timezone.now().date() and self.status == ReminderStatusChoices.PENDING

    def mark_as_sent(self):
        """Mark reminder as sent"""
        self.status = ReminderStatusChoices.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

