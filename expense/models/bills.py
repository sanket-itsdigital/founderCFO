from decimal import Decimal
from datetime import timedelta
import re

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import BillsStatusChoices, InvoicesPaymentTerms
from financial.models.account_payable.vendor import Vendor


class Bill(BaseModel):
    """Expense Bill model with comprehensive fields"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="expense_bills",
    )

    # Basic Bill Information
    bill_number = models.CharField(max_length=100)
    bill_date = models.DateField()
    due_date = models.DateField()

    # Vendor Information
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="expense_bills",
        null=True,
        blank=True,
    )
    vendor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legacy field, use vendor FK when possible",
    )
    vendor_gstin = models.CharField(
        max_length=15,
        blank=True,
        help_text="Vendor GST Identification Number",
    )
    vendor_pan = models.CharField(
        max_length=10,
        blank=True,
        help_text="Vendor PAN Number",
    )
    is_vendor_out_of_india = models.BooleanField(
        default=False,
        help_text="Check if vendor is outside India",
    )

    # Item/Service Information
    item_name = models.CharField(max_length=255, blank=True)
    hsn_sac = models.CharField(max_length=10, blank=True, help_text="HSN/SAC Code")
    category = models.CharField(max_length=100, blank=True)

    # Location Information
    place_of_supply = models.CharField(max_length=255, blank=True)

    # Amounts
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Subtotal before taxes",
    )

    # GST Details
    cgst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="CGST percentage (e.g., 9.00 for 9%)",
    )
    cgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="CGST Amount = CGST % * SubTotal",
    )
    sgst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="SGST percentage (e.g., 9.00 for 9%)",
    )
    sgst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="SGST Amount = SGST % * SubTotal",
    )
    igst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="IGST percentage (e.g., 18.00 for 18%)",
    )
    igst_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="IGST Amount = IGST % * SubTotal",
    )

    # TDS Details
    tds_section = models.CharField(
        max_length=50,
        blank=True,
        help_text="TDS Section (e.g., 194A, 194C)",
    )
    tds_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="TDS percentage (e.g., 2.00 for 2%)",
    )
    tds_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="TDS Amount = TDS % * SubTotal",
    )

    # Total Amount
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total = SubTotal + CGST + SGST + IGST - TDS",
    )

    # Payment Information
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        choices=InvoicesPaymentTerms.choices,
        help_text="Payment terms (e.g., Net 30)",
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Status
    status = models.CharField(
        max_length=50,
        choices=BillsStatusChoices.choices,
        default=BillsStatusChoices.PENDING,
    )

    # Organizational Information
    branch = models.CharField(max_length=255, blank=True)
    branch_gstin = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100, blank=True)

    # Additional Fields
    eligibility = models.CharField(max_length=100, blank=True)
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this is a recurring bill",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "expense_bill"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-bill_date"]
        unique_together = ["company", "bill_number"]

    def __str__(self):
        return f"{self.bill_number} - {self.get_vendor_name()}"

    def get_vendor_name(self):
        """Get vendor name from FK or legacy field"""
        if self.vendor:
            return self.vendor.name
        return self.vendor_name or "Unknown Vendor"

    @staticmethod
    def _parse_payment_terms(payment_terms):
        """Parse payment terms string to get number of days"""
        if not payment_terms:
            return 0

        # Handle COD
        if payment_terms.upper() == "COD":
            return 0

        # Extract number from "Net 30", "Net 15", etc.
        match = re.search(r"\d+", payment_terms)
        if match:
            return int(match.group())
        return 0

    def calculate_due_date(self):
        """Calculate due_date from bill_date + payment_terms"""
        if not self.bill_date:
            return None

        days = self._parse_payment_terms(self.payment_terms)
        return self.bill_date + timedelta(days=days)

    def calculate_cgst_amount(self):
        """Calculate CGST Amount = CGST % * SubTotal"""
        if self.cgst_percentage and self.subtotal:
            return (self.cgst_percentage / Decimal("100.00")) * self.subtotal
        return Decimal("0.00")

    def calculate_sgst_amount(self):
        """Calculate SGST Amount = SGST % * SubTotal"""
        if self.sgst_percentage and self.subtotal:
            return (self.sgst_percentage / Decimal("100.00")) * self.subtotal
        return Decimal("0.00")

    def calculate_igst_amount(self):
        """Calculate IGST Amount = IGST % * SubTotal"""
        if self.igst_percentage and self.subtotal:
            return (self.igst_percentage / Decimal("100.00")) * self.subtotal
        return Decimal("0.00")

    def calculate_tds_amount(self):
        """Calculate TDS Amount = TDS % * SubTotal"""
        if self.tds_percentage and self.subtotal:
            return (self.tds_percentage / Decimal("100.00")) * self.subtotal
        return Decimal("0.00")

    def calculate_total(self):
        """Calculate Total = SubTotal + CGST + SGST + IGST - TDS"""
        total = self.subtotal
        total += self.cgst_amount
        total += self.sgst_amount
        total += self.igst_amount
        total -= self.tds_amount
        return max(total, Decimal("0.00"))

    def clean(self):
        """Validate GST and PAN fields"""
        errors = {}

        # Check if vendor is out of India or doesn't have GST
        should_skip_gst = (
            self.is_vendor_out_of_india
            or (self.vendor and not self.vendor.gstin)
            or (not self.vendor and not self.vendor_gstin)
        )

        # If GST should be skipped, allow empty GSTIN and PAN
        if not should_skip_gst:
            # If vendor is in India and has GST, validate GSTIN format
            if self.vendor and self.vendor.gstin:
                if len(self.vendor.gstin) != 15:
                    errors["vendor_gstin"] = "GSTIN must be 15 characters"
            elif self.vendor_gstin:
                if len(self.vendor_gstin) != 15:
                    errors["vendor_gstin"] = "GSTIN must be 15 characters"

        # Validate PAN format if provided
        if self.vendor_pan and len(self.vendor_pan) != 10:
            errors["vendor_pan"] = "PAN must be 10 characters"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Auto-calculate amounts and update status"""
        # Calculate GST amounts
        self.cgst_amount = self.calculate_cgst_amount()
        self.sgst_amount = self.calculate_sgst_amount()
        self.igst_amount = self.calculate_igst_amount()

        # Calculate TDS amount
        self.tds_amount = self.calculate_tds_amount()

        # Calculate total
        self.total = self.calculate_total()

        # Calculate due_date from bill_date + payment_terms if payment_terms is provided
        if self.payment_terms and self.bill_date:
            calculated_due_date = self.calculate_due_date()
            if calculated_due_date:
                self.due_date = calculated_due_date

        # Sync vendor information
        if self.vendor:
            if not self.vendor_name:
                self.vendor_name = self.vendor.name
            if not self.vendor_gstin and self.vendor.gstin:
                self.vendor_gstin = self.vendor.gstin
            if not self.vendor_pan and self.vendor.pan:
                self.vendor_pan = self.vendor.pan

        # Auto-update status based on payments
        if self.status in [BillsStatusChoices.PENDING, BillsStatusChoices.PARTIAL]:
            if self.paid_amount >= self.total:
                self.status = BillsStatusChoices.PAID
            elif self.is_overdue:
                self.status = BillsStatusChoices.OVERDUE
            elif self.paid_amount > 0:
                self.status = BillsStatusChoices.PARTIAL
            else:
                self.status = BillsStatusChoices.PENDING

        super().save(*args, **kwargs)

    @property
    def amount(self):
        """Backward compatibility: return total as amount"""
        return self.total

    @property
    def balance_amount(self):
        """Calculate outstanding amount: total - paid_amount"""
        return self.total - self.paid_amount

    @property
    def is_overdue(self):
        """Check if the bill is overdue"""
        return self.due_date < timezone.now().date() and self.status not in [
            BillsStatusChoices.PAID,
            BillsStatusChoices.CANCELLED,
        ]











