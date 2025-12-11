from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import InvoicesStatusChoices, InvoicesPaymentTerms


class Invoice(BaseModel):
    """Revenue Invoice model with comprehensive fields"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="revenue_invoices",
    )

    # Basic Invoice Information
    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    due_date = models.DateField()

    # Customer Information
    customer_name = models.CharField(max_length=255)
    customer_gstin = models.CharField(max_length=15, blank=True)

    # Product/Service Information
    product_name = models.CharField(max_length=255)
    service_type = models.CharField(max_length=100, blank=True)
    hsn_sac_code = models.CharField(max_length=10, blank=True)

    # Location Information
    place_of_supply = models.CharField(max_length=255, blank=True)

    # Quantity and Pricing
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    taxable_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # GST Details
    cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    cgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    sgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    igst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Total Amount
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Status and Payment
    status = models.CharField(
        max_length=20,
        choices=InvoicesStatusChoices.choices,
        default=InvoicesStatusChoices.DRAFT,
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        choices=InvoicesPaymentTerms.choices,
    )

    # Sales Information
    salesperson = models.CharField(max_length=255, blank=True)

    # Geographic Information
    region = models.CharField(max_length=100, blank=True)
    territory = models.CharField(max_length=100, blank=True)

    # Organizational Information
    department = models.CharField(max_length=100, blank=True)

    # Branch Information
    branch = models.CharField(max_length=255, blank=True)
    branch_gstin = models.CharField(max_length=15, blank=True)

    # Project Information
    project_id = models.CharField(max_length=100, blank=True)
    project_name = models.CharField(max_length=255, blank=True)

    # Billing Information
    billing_type = models.CharField(max_length=50, blank=True)
    billable_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Recurring Information
    is_recurring = models.BooleanField(default=False)

    # Additional Information
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "revenue_invoice"
        verbose_name = "Revenue Invoice"
        verbose_name_plural = "Revenue Invoices"
        ordering = ["-invoice_date"]
        unique_together = [["company", "invoice_number"]]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"

    def save(self, *args, **kwargs):
        """Auto-calculate amounts if not provided"""
        # Calculate taxable value if not set
        if not self.taxable_value and self.quantity and self.unit_price:
            self.taxable_value = self.quantity * self.unit_price

        # Calculate GST amounts if rates are provided
        if self.cgst_rate > 0 and not self.cgst_amount:
            self.cgst_amount = (self.taxable_value * self.cgst_rate) / Decimal("100")

        if self.sgst_rate > 0 and not self.sgst_amount:
            self.sgst_amount = (self.taxable_value * self.sgst_rate) / Decimal("100")

        if self.igst_rate > 0 and not self.igst_amount:
            self.igst_amount = (self.taxable_value * self.igst_rate) / Decimal("100")

        # Calculate total amount if not set
        if not self.total_amount:
            self.total_amount = (
                self.taxable_value
                + self.cgst_amount
                + self.sgst_amount
                + self.igst_amount
            )

        super().save(*args, **kwargs)
