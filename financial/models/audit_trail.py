from django.db import models
from django.utils import timezone

from accounts.models import Company, User
from backend.models import BaseModel


class AuditTrail(BaseModel):
    """Audit trail for tracking all system actions"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="audit_trails",
        null=True,
        blank=True,
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ("create", "Create"),
            ("update", "Update"),
            ("payment", "Payment"),
            ("email", "Email"),
            ("call", "Call"),
            ("status_change", "Status Change"),
            ("dispute", "Dispute"),
            ("write_off", "Write Off"),
        ],
    )
    entity_type = models.CharField(
        max_length=50,
        choices=[
            ("invoice", "Invoice"),
            ("payment", "Payment"),
            ("customer", "Customer"),
            ("reminder", "Reminder"),
            ("dispute", "Dispute"),
            ("write_off", "Write Off"),
            ("factoring", "Factoring"),
            ("payment_plan", "Payment Plan"),
        ],
    )
    entity_id = models.UUIDField(
        help_text="ID of the entity that was acted upon"
    )
    reference = models.CharField(
        max_length=255,
        help_text="Reference number or identifier (e.g., invoice number)"
    )
    details = models.TextField(
        help_text="Description of the action"
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON representation of changes (e.g., {'status': 'pending'} -> {'status': 'paid'})"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_trails",
        help_text="User who performed the action (null for system actions)"
    )

    class Meta:
        db_table = "audit_trail"
        verbose_name = "Audit Trail"
        verbose_name_plural = "Audit Trails"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["action", "entity_type"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.entity_type} - {self.reference}"

    @classmethod
    def log_action(
        cls,
        action,
        entity_type,
        entity_id,
        reference,
        details,
        company=None,
        user=None,
        changes=None,
    ):
        """Helper method to log an audit trail entry"""
        return cls.objects.create(
            company=company,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            reference=reference,
            details=details,
            changes=changes,
            user=user,
        )

