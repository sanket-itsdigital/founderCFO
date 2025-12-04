from django.db import models
from accounts.models import Company
from backend.models import BaseModel


class Vendor(BaseModel):
    """Vendor model for managing vendor information"""
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vendors",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True, help_text="GST Identification Number")
    pan = models.CharField(max_length=10, blank=True, null=True, help_text="PAN Number")
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "vendor"
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        unique_together = ["company", "name"]
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else ''}"

