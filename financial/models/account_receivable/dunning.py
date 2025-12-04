from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import DunningStageChoices
from financial.models.account_receivable import Invoice


class EmailTemplate(BaseModel):
    """Email templates for dunning and reminders"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="email_templates",
        null=True,
        blank=True,
        help_text="If null, template is available to all companies"
    )
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=500)
    body = models.TextField()
    template_type = models.CharField(
        max_length=50,
        default="reminder",
        help_text="Type of template: reminder, dunning, etc."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "email_template"
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else 'Global'}"


class DunningQueue(BaseModel):
    """Queue of invoices that need dunning reminders"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="dunning_queues",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="dunning_queues",
    )
    stage = models.CharField(
        max_length=20,
        choices=DunningStageChoices.choices,
    )
    days_overdue = models.IntegerField()
    last_sent_at = models.DateTimeField(null=True, blank=True)
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dunning_queues",
    )

    class Meta:
        db_table = "dunning_queue"
        verbose_name = "Dunning Queue"
        verbose_name_plural = "Dunning Queues"
        ordering = ["-days_overdue"]
        unique_together = ["company", "invoice", "stage"]

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.get_stage_display()}"

    @staticmethod
    def calculate_stage(days_overdue):
        """Calculate dunning stage based on days overdue"""
        if days_overdue >= 60:
            return DunningStageChoices.FINAL
        elif days_overdue >= 30:
            return DunningStageChoices.URGENT
        elif days_overdue >= 15:
            return DunningStageChoices.FIRM
        else:
            return DunningStageChoices.FRIENDLY

    def update_stage(self):
        """Update stage based on current days overdue"""
        today = timezone.now().date()
        days_overdue = (today - self.invoice.due_date).days
        self.days_overdue = days_overdue
        self.stage = self.calculate_stage(days_overdue)
        self.save(update_fields=['days_overdue', 'stage'])

