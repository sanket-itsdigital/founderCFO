from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from revenue.models.invoice import Invoice


class FactoringRequest(BaseModel):
    """Invoice factoring requests"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="factoring_requests",
    )
    advance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
        help_text="Advance rate percentage (typically 70-90%)",
    )
    factoring_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("2.50"),
        help_text="Factoring fee percentage",
    )
    processing_time_days = models.IntegerField(
        default=2, help_text="Processing time in days"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("completed", "Completed"),
        ],
        default="draft",
    )
    total_receivables = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    advance_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    factoring_fee_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    net_proceeds = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    reserve_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        db_table = "factoring_request"
        verbose_name = "Factoring Request"
        verbose_name_plural = "Factoring Requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Factoring Request - {self.company.name} - {self.status}"

    def calculate_amounts(self, selected_invoices):
        """Calculate factoring amounts based on selected invoices"""
        total_receivables = sum(invoice.balance_amount for invoice in selected_invoices)
        self.total_receivables = total_receivables

        # Calculate advance amount
        advance_rate_decimal = self.advance_rate / 100
        self.advance_amount = total_receivables * advance_rate_decimal

        # Calculate factoring fee
        fee_rate_decimal = self.factoring_fee / 100
        self.factoring_fee_amount = total_receivables * fee_rate_decimal

        # Calculate net proceeds (advance - fee)
        self.net_proceeds = self.advance_amount - self.factoring_fee_amount

        # Calculate reserve (remaining amount held back)
        self.reserve_amount = total_receivables - self.advance_amount

        self.save(
            update_fields=[
                "total_receivables",
                "advance_amount",
                "factoring_fee_amount",
                "net_proceeds",
                "reserve_amount",
            ]
        )

    @property
    def annualized_cost(self):
        """Calculate annualized cost of factoring"""
        if self.total_receivables == 0:
            return 0.0

        # Simplified calculation: (Fee / Advance) * (365 / Avg Days to Due)
        # This is a simplified version; actual calculation may vary
        avg_days = 30  # Default assumption
        if self.invoices.exists():
            total_days = sum(
                (invoice.due_date - timezone.now().date()).days
                for invoice in self.invoices.all()
            )
            avg_days = (
                total_days / self.invoices.count() if self.invoices.count() > 0 else 30
            )

        if avg_days <= 0:
            return 0.0

        cost_rate = (
            (self.factoring_fee_amount / self.advance_amount)
            if self.advance_amount > 0
            else 0
        )
        annualized = cost_rate * (365 / avg_days) * 100
        return float(annualized)


class FactoringRequestInvoice(BaseModel):
    """Invoices included in a factoring request"""

    factoring_request = models.ForeignKey(
        FactoringRequest,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="factoring_requests",
    )

    class Meta:
        db_table = "factoring_request_invoice"
        verbose_name = "Factoring Request Invoice"
        verbose_name_plural = "Factoring Request Invoices"
        unique_together = ["factoring_request", "invoice"]

    def __str__(self):
        return f"{self.factoring_request} - {self.invoice.invoice_number}"
