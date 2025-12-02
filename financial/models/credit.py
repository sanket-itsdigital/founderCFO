from decimal import Decimal

from django.db import models
from django.db.models import Sum, Avg, F
from django.utils import timezone

from accounts.models import Company
from backend.models import BaseModel
from financial.enums import RiskLevelChoices, InvoicesStatusChoices


class Credit(BaseModel):
    """
    Customer Credit Limits model to track credit extended to customers.
    Only the credit_limit field can be updated by users.
    Other fields are calculated from invoice data.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="credits",
    )
    customer_name = models.CharField(max_length=255)
    credit_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Maximum credit limit extended to the customer (editable)",
    )
    
    # Calculated fields (stored for performance, but can be recalculated)
    payment_score = models.IntegerField(
        default=0,
        help_text="Payment score out of 100 (calculated from payment history)",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevelChoices.choices,
        default=RiskLevelChoices.LOW,
        help_text="Risk level based on payment behavior and utilization",
    )
    avg_days_to_pay = models.IntegerField(
        default=0,
        help_text="Average number of days taken to pay invoices",
    )

    class Meta:
        db_table = "credit"
        verbose_name = "Credit"
        verbose_name_plural = "Credits"
        ordering = ["customer_name"]
        unique_together = ["company", "customer_name"]

    def __str__(self):
        return f"{self.customer_name} - {self.company.name}"

    @property
    def current_balance(self):
        """Calculate current outstanding balance from invoices"""
        from financial.models.account_receivable import Invoice
        from django.db.models import F
        
        invoices = Invoice.objects.filter(
            company=self.company,
            customer_name=self.customer_name
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )
        
        total = Decimal("0.00")
        for invoice in invoices:
            balance = invoice.balance_amount  # Use the property
            total += balance
        
        return total

    @property
    def utilization_percentage(self):
        """Calculate credit utilization percentage"""
        if self.credit_limit == 0:
            return 0.0
        balance = self.current_balance
        return float((balance / self.credit_limit) * 100)

    def calculate_payment_score(self):
        """Calculate payment score based on payment history"""
        from financial.models.account_receivable import Invoice
        
        # Get all paid invoices for this customer
        paid_invoices = Invoice.objects.filter(
            company=self.company,
            customer_name=self.customer_name,
            status=InvoicesStatusChoices.PAID
        )
        
        if not paid_invoices.exists():
            return 50  # Default score if no payment history
        
        total_score = 0
        count = 0
        
        for invoice in paid_invoices:
            # Calculate days to pay
            days_to_pay = (invoice.updated_at.date() - invoice.due_date).days
            
            # Score based on payment timing
            if days_to_pay <= 0:
                score = 100  # Paid on time or early
            elif days_to_pay <= 7:
                score = 90
            elif days_to_pay <= 15:
                score = 80
            elif days_to_pay <= 30:
                score = 70
            elif days_to_pay <= 60:
                score = 50
            else:
                score = 30
            
            total_score += score
            count += 1
        
        return int(total_score / count) if count > 0 else 50

    def calculate_avg_days_to_pay(self):
        """Calculate average days to pay from paid invoices"""
        from financial.models.account_receivable import Invoice
        
        paid_invoices = Invoice.objects.filter(
            company=self.company,
            customer_name=self.customer_name,
            status=InvoicesStatusChoices.PAID
        )
        
        if not paid_invoices.exists():
            return 0
        
        total_days = 0
        count = 0
        
        for invoice in paid_invoices:
            days_to_pay = (invoice.updated_at.date() - invoice.due_date).days
            total_days += days_to_pay
            count += 1
        
        return int(total_days / count) if count > 0 else 0

    def calculate_risk_level(self):
        """Calculate risk level based on utilization, payment score, and overdue invoices"""
        from financial.models.account_receivable import Invoice
        
        utilization = self.utilization_percentage
        payment_score = self.calculate_payment_score()
        
        # Check for overdue invoices
        overdue_count = Invoice.objects.filter(
            company=self.company,
            customer_name=self.customer_name,
            status=InvoicesStatusChoices.OVERDUE
        ).count()
        
        # Risk calculation
        if utilization >= 90 or payment_score < 50 or overdue_count > 3:
            return RiskLevelChoices.HIGH
        elif utilization >= 70 or payment_score < 70 or overdue_count > 1:
            return RiskLevelChoices.MEDIUM
        else:
            return RiskLevelChoices.LOW

    def save(self, *args, **kwargs):
        """Override save to update calculated fields if needed"""
        # Check if this is a new instance
        is_new = self.pk is None
        
        # If updating, check if credit_limit changed
        credit_limit_changed = False
        if not is_new:
            try:
                old_instance = Credit.objects.get(pk=self.pk)
                credit_limit_changed = old_instance.credit_limit != self.credit_limit
            except Credit.DoesNotExist:
                is_new = True
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Update calculated fields for new instances or when credit_limit changes
        if is_new or credit_limit_changed:
            # Use update_fields to avoid recursion
            self.payment_score = self.calculate_payment_score()
            self.avg_days_to_pay = self.calculate_avg_days_to_pay()
            self.risk_level = self.calculate_risk_level()
            super().save(update_fields=['payment_score', 'avg_days_to_pay', 'risk_level'])

